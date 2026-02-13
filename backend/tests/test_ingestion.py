"""
Tests for ingestion pipeline.

Component 1.4 in COMPONENT_SPEC.md.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from models.proposition import ConversationMessage
from services.extraction.models import Proposition
from services.storage.sqlite_storage import SQLiteStorage
from services.ingestion import IngestionService


# --- Mock classes ---


class MockExtractionService:
    """Mock extraction — returns 2 predictable propositions for any input text."""

    async def extract(self, text: str) -> list[Proposition]:
        return [
            Proposition(
                proposition=f"Belief extracted from: {text[:30]}",
                node_type="belief",
                confidence=0.9,
            ),
            Proposition(
                proposition=f"Observation extracted from: {text[:30]}",
                node_type="observation",
                confidence=0.8,
            ),
        ]


class FailingExtractionService:
    """Mock extraction — always raises an error. For error handling test."""

    async def extract(self, text: str) -> list[Proposition]:
        raise Exception("LLM extraction failed")


class SelectiveExtractionService:
    """Fails on specific text, succeeds on everything else."""

    def __init__(self, fail_on: str):
        self._fail_on = fail_on
        self._normal = MockExtractionService()

    async def extract(self, text: str) -> list[Proposition]:
        if self._fail_on in text:
            raise Exception("LLM extraction failed")
        return await self._normal.extract(text)


class MockEmbeddingProvider:
    """Mock embedder — deterministic vectors from text hash."""

    def embed(self, text: str) -> np.ndarray:
        # Same text → same vector, different text → different vector
        seed = hash(text) % (2**32)
        rng = np.random.RandomState(seed)
        vec = rng.randn(768).astype(np.float32)
        return vec / np.linalg.norm(vec)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return np.vstack([self.embed(t) for t in texts])

    @property
    def dimensions(self) -> int:
        return 768

    @property
    def model_name(self) -> str:
        return "mock-embedding"


# --- Fixtures ---


@pytest.fixture
def storage(tmp_path):
    db = SQLiteStorage(tmp_path / "test.db")
    yield db
    db.close()


@pytest.fixture
def mock_extractor():
    return MockExtractionService()


@pytest.fixture
def mock_embedder():
    return MockEmbeddingProvider()


@pytest.fixture
def ingestion(storage, mock_extractor, mock_embedder):
    return IngestionService(
        storage=storage,
        extraction=mock_extractor,
        embedder=mock_embedder,
    )


@pytest.fixture
def sample_message():
    """A single user message for basic tests."""
    return ConversationMessage(
        text="I think my ankle limits my rowing performance",
        speaker="user",
        timestamp=datetime(2026, 2, 10, 21, 53, 12),
        session_id="session-abc",
        message_index=0,
        source_char_start=100,
        source_char_end=200,
        source_file="test_conversation.md",
        assistant_reasoning=None,
    )


@pytest.fixture
def conversation_messages():
    """A full conversation with 3 user + 2 assistant messages."""
    return [
        ConversationMessage(
            text="I think my ankle limits my rowing performance",
            speaker="user",
            timestamp=datetime(2026, 2, 10, 21, 53, 12),
            session_id="session-abc",
            message_index=0,
            source_char_start=100,
            source_char_end=200,
            source_file="test_conversation.md",
            assistant_reasoning=None,
        ),
        ConversationMessage(
            text="That makes sense given the ROM limitation.",
            speaker="assistant",
            timestamp=datetime(2026, 2, 10, 21, 53, 30),
            session_id="session-abc",
            message_index=1,
            source_char_start=200,
            source_char_end=300,
            source_file="test_conversation.md",
            assistant_reasoning="Thought about ankle anatomy...",
        ),
        ConversationMessage(
            text="I've been doing breathing drills and they help a lot",
            speaker="user",
            timestamp=datetime(2026, 2, 10, 21, 54, 0),
            session_id="session-abc",
            message_index=2,
            source_char_start=300,
            source_char_end=400,
            source_file="test_conversation.md",
            assistant_reasoning=None,
        ),
        ConversationMessage(
            text="Breathing mechanics directly affect power output.",
            speaker="assistant",
            timestamp=datetime(2026, 2, 10, 21, 54, 15),
            session_id="session-abc",
            message_index=3,
            source_char_start=400,
            source_char_end=500,
            source_file="test_conversation.md",
            assistant_reasoning="Considered respiratory drive...",
        ),
        ConversationMessage(
            text="My 2K target is 8:05 and I want to break 8 minutes",
            speaker="user",
            timestamp=datetime(2026, 2, 10, 21, 55, 0),
            session_id="session-abc",
            message_index=4,
            source_char_start=500,
            source_char_end=600,
            source_file="test_conversation.md",
            assistant_reasoning=None,
        ),
    ]


# --- Tests ---


@pytest.mark.asyncio
async def test_ingest_single_message(ingestion, storage, sample_message):
    """Ingest single message → propositions stored in SQLite."""
    result = await ingestion.ingest_message(sample_message)

    # MockExtractionService returns 2 propositions per message
    assert result.propositions_extracted == 2
    assert result.propositions_stored == 2
    assert result.duplicates_found == 0
    assert result.session_id == "session-abc"

    # Verify they're actually in the database
    stored = storage.find_by_session("session-abc")
    assert len(stored) == 2
    assert stored[0].node_type == "belief"
    assert stored[1].node_type == "observation"


@pytest.mark.asyncio
async def test_ingest_duplicate_proposition(ingestion, storage, sample_message):
    """Ingest same message twice → dedup fires on second pass."""
    result1 = await ingestion.ingest_message(sample_message)
    assert result1.propositions_stored == 2

    # Ingest the exact same message again
    result2 = await ingestion.ingest_message(sample_message)
    assert result2.propositions_extracted == 2
    assert result2.duplicates_found == 2
    assert result2.propositions_stored == 0

    # Database should still only have 2 propositions
    stored = storage.find_by_session("session-abc")
    assert len(stored) == 2


@pytest.mark.asyncio
async def test_ingest_full_conversation(ingestion, storage, conversation_messages):
    """Ingest conversation → user messages processed, assistant skipped."""
    result = await ingestion.ingest_conversation(conversation_messages)

    # 5 messages total, 3 are user, 2 are assistant (skipped)
    assert result.total_messages == 5
    # 3 user messages × 2 propositions each = 6
    assert result.total_propositions_extracted == 6
    assert result.sessions_processed == 1

    # All stored propositions should be in the database
    stored = storage.find_by_session("session-abc")
    assert len(stored) == result.total_propositions_stored


@pytest.mark.asyncio
async def test_ingest_directory(ingestion, storage, tmp_path):
    """Ingest directory → multiple sessions processed."""
    # Create minimal fixture files that the parser can handle
    fixtures_dir = Path(__file__).parent / "fixtures" / "real"

    result = await ingestion.ingest_directory(fixtures_dir)

    assert result.sessions_processed >= 2
    assert result.total_propositions_stored > 0


@pytest.mark.asyncio
async def test_ingest_error_handling(storage, mock_embedder, conversation_messages):
    """Extraction fails on one message → others still processed."""
    # This extractor fails on the ankle message, succeeds on others
    selective_extractor = SelectiveExtractionService(fail_on="ankle")
    ingestion = IngestionService(
        storage=storage,
        extraction=selective_extractor,
        embedder=mock_embedder,
    )

    result = await ingestion.ingest_conversation(conversation_messages)

    # 3 user messages, 1 fails (ankle), 2 succeed × 2 propositions each = 4
    assert result.total_propositions_extracted == 4
    assert result.total_propositions_stored == 4
    assert len(result.errors) == 1
    assert "ankle" in result.errors[0] or "failed" in result.errors[0].lower()
