"""
Extraction API route — extract propositions from a completed conversation.

POST /api/extract/{conversation_id}
  1. Reads messages from voku.db (conversation store)
  2. Filters to user messages, formats as conversation text
  3. Runs ConversationExtractionService (Groq) → propositions
  4. Embeds each with BGE, dedup-checks, stores in m2_conversation.db

Designed to be called fire-and-forget when the user clicks "+new".
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.conversation.service import ConversationService
from app.services.extraction.conversation_extractor import (
    ConversationExtractionService,
    ConversationExtractionResult,
)
from app.services.extraction.models import ExtractionError
from app.services.providers.groq_provider import GroqProvider
from app.services.providers.base import ProviderError
from app.services.storage.models import StoredProposition
from app.dependencies import propositions_storage, embedder
from app.routes.propositions import invalidate_cache

router = APIRouter(prefix="/api", tags=["extraction"])

DEDUP_THRESHOLD = 0.95


class ExtractionResponse(BaseModel):
    conversation_id: str
    messages_found: int
    user_messages: int
    propositions_extracted: int
    propositions_stored: int
    duplicates_skipped: int
    summary: str


@router.post("/extract/{conversation_id}", response_model=ExtractionResponse)
async def extract_conversation(conversation_id: str):
    """Extract propositions from a completed conversation."""

    # 1. Read messages from conversation database (voku.db)
    conv_service = ConversationService(settings.db_path)
    try:
        messages = conv_service.get_conversation_messages(conversation_id)
    finally:
        conv_service.close()

    if not messages:
        raise HTTPException(
            status_code=404,
            detail=f"No messages found for conversation {conversation_id}",
        )

    # 2. Filter and format — user messages only for extraction,
    #    but include assistant messages for context (the LLM reads both
    #    to understand the conversation arc, extracts from user only)
    user_messages = [m for m in messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(
            status_code=400,
            detail="Conversation has no user messages to extract from",
        )

    # Format as labeled dialogue (same format batch script used successfully)
    conversation_text = ""
    for msg in messages:
        label = "User" if msg.role == "user" else "Assistant"
        conversation_text += f"{label}: {msg.content}\n\n"

    # 3. Extract via Groq
    provider = GroqProvider()
    extractor = ConversationExtractionService(provider)

    try:
        result: ConversationExtractionResult = await extractor.extract(
            conversation_text
        )
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {e}")
    except ExtractionError as e:
        raise HTTPException(status_code=422, detail=f"Extraction parse error: {e}")

    # 4. Embed, dedup, store
    now = datetime.now(timezone.utc).isoformat()
    stored_count = 0
    dupe_count = 0

    for prop in result.propositions:
        # Embed
        embedding = embedder.embed(prop.proposition)

        # Dedup against existing propositions
        similar = propositions_storage.find_similar(
            embedding, threshold=DEDUP_THRESHOLD
        )
        if similar:
            dupe_count += 1
            continue

        # Store
        stored_prop = StoredProposition(
            id=str(uuid.uuid4()),
            text=prop.proposition,
            node_type=prop.node_type,
            confidence=prop.confidence,
            supersedable=prop.supersedable,
            event_timeframe=prop.event_timeframe,
            superseded_in_conversation=prop.superseded_in_conversation,
            conversation_summary=result.conversation_summary,
            source_type="conversation",
            created_at=now,
            session_id=conversation_id,
            status="active",
        )

        propositions_storage.store_proposition(stored_prop)
        propositions_storage.store_embedding(
            stored_prop.id, embedding, embedder.model_name
        )
        stored_count += 1

    # Invalidate projection cache so next /api/propositions re-runs UMAP
    if stored_count > 0:
        invalidate_cache()

    return ExtractionResponse(
        conversation_id=conversation_id,
        messages_found=len(messages),
        user_messages=len(user_messages),
        propositions_extracted=len(result.propositions),
        propositions_stored=stored_count,
        duplicates_skipped=dupe_count,
        summary=result.conversation_summary,
    )
