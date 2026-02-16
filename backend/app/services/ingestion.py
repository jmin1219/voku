"""
Ingestion pipeline — orchestrates import → extract → embed → dedup → store.

Component 1.4 in COMPONENT_SPEC.md.
Replaces old ChatService.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from models.proposition import ConversationMessage

from services.extraction.models import Proposition
from services.storage.models import StoredProposition

# Dedup threshold — cosine similarity above this means "same proposition"
DEDUP_THRESHOLD = 0.95

# Messages shorter than this are skipped (commands, "yes", "continue", etc.)
MIN_MESSAGE_LENGTH = 30

# User message position tracking for AI-mediation confidence signal
# Earlier messages in conversation = less AI-mediated = higher signal quality


@dataclass
class IngestionResult:
    """Result of ingesting a single message."""

    propositions_extracted: int = 0
    propositions_stored: int = 0
    duplicates_found: int = 0
    session_id: str | None = None


@dataclass
class BatchIngestionResult:
    """Result of ingesting a conversation or directory."""

    total_messages: int = 0
    total_propositions_extracted: int = 0
    total_propositions_stored: int = 0
    sessions_processed: int = 0
    errors: list[str] = field(default_factory=list)


class IngestionService:
    """Orchestrates extract → embed → dedup → store for conversation messages."""

    def __init__(self, storage, extraction, embedder, throttle_seconds: float = 0):
        self._storage = storage
        self._extraction = extraction
        self._embedder = embedder
        self._throttle = throttle_seconds

    # ------------------------------------------------------------------
    # Core: single message
    # ------------------------------------------------------------------

    async def ingest_message(
        self,
        message: ConversationMessage,
        ai_context: str | None = None,
        user_message_position: int | None = None,
    ) -> IngestionResult:
        """Ingest a single message: extract propositions, embed, dedup, store.

        Args:
            message: The user message to ingest.
            ai_context: Optional preceding AI message text for extraction comprehension.
            user_message_position: Position of this user message among all user messages
                in the conversation (0-indexed). Earlier = less AI-mediated.
        """
        result = IngestionResult(session_id=message.session_id)

        # 1. Extract propositions (async LLM call, with optional AI context)
        propositions: list[Proposition] = await self._extraction.extract(
            message.text, ai_context=ai_context
        )
        result.propositions_extracted = len(propositions)

        # 2–4. For each proposition: embed → dedup → store
        for prop in propositions:
            embedding = self._embedder.embed(prop.proposition)

            # Dedup: check if a near-identical proposition already exists
            similar = self._storage.find_similar(embedding, threshold=DEDUP_THRESHOLD)
            if similar:
                result.duplicates_found += 1
                continue

            # Build StoredProposition with provenance from the message
            stored_prop = StoredProposition(
                id=str(uuid.uuid4()),
                text=prop.proposition,
                node_type=prop.node_type,
                confidence=prop.confidence,
                supersedable=prop.supersedable,
                event_timeframe=prop.event_timeframe,
                source_type="conversation",
                created_at=datetime.now(timezone.utc).isoformat(),
                session_id=message.session_id,
                message_index=message.message_index,
                message_position=user_message_position,
                source_char_start=message.source_char_start,
                source_char_end=message.source_char_end,
                source_file=message.source_file,
            )

            self._storage.store_proposition(stored_prop)
            self._storage.store_embedding(
                stored_prop.id, embedding, self._embedder.model_name
            )
            result.propositions_stored += 1

        return result

    # ------------------------------------------------------------------
    # Batch: full conversation
    # ------------------------------------------------------------------

    async def ingest_conversation(
        self, messages: list[ConversationMessage]
    ) -> BatchIngestionResult:
        """Ingest a list of messages — only user messages are processed.

        AI messages are passed as comprehension context to the extraction LLM
        but never extracted from directly.
        """
        batch = BatchIngestionResult(total_messages=len(messages))
        sessions_seen: set[str] = set()

        # Track preceding AI message for context and user message position
        last_ai_message: str | None = None
        user_msg_position = 0

        for msg in messages:
            if msg.speaker != "user":
                # Track the most recent AI message for context
                last_ai_message = msg.text.strip() if msg.text else None
                continue

            # Pre-filter: skip short messages that won't produce propositions
            if len(msg.text.strip()) < MIN_MESSAGE_LENGTH:
                user_msg_position += 1
                last_ai_message = None  # Reset after user message
                continue

            sessions_seen.add(msg.session_id)

            try:
                result = await self.ingest_message(
                    msg,
                    ai_context=last_ai_message,
                    user_message_position=user_msg_position,
                )
                batch.total_propositions_extracted += result.propositions_extracted
                batch.total_propositions_stored += result.propositions_stored
            except Exception as e:
                batch.errors.append(f"Message {msg.message_index}: {e}")

            user_msg_position += 1
            last_ai_message = None  # Reset after processing

            # Throttle between extraction calls to respect rate limits
            if self._throttle > 0:
                await asyncio.sleep(self._throttle)

        batch.sessions_processed = len(sessions_seen)
        return batch

    # ------------------------------------------------------------------
    # Batch: directory of markdown files
    # ------------------------------------------------------------------

    async def ingest_directory(self, dirpath: Path) -> BatchIngestionResult:
        """Ingest all markdown files in a directory."""
        from services.parser import ConversationParser

        parser = ConversationParser()
        aggregate = BatchIngestionResult()
        sessions_seen: set[str] = set()

        for filepath in sorted(dirpath.glob("*.md")):
            try:
                messages = parser.parse_file(filepath)
            except Exception as e:
                aggregate.errors.append(f"Parse {filepath.name}: {e}")
                continue

            result = await self.ingest_conversation(messages)
            aggregate.total_messages += result.total_messages
            aggregate.total_propositions_extracted += (
                result.total_propositions_extracted
            )
            aggregate.total_propositions_stored += result.total_propositions_stored
            aggregate.errors.extend(result.errors)
            sessions_seen.update(
                msg.session_id for msg in messages if msg.speaker == "user"
            )

        aggregate.sessions_processed = len(sessions_seen)
        return aggregate
