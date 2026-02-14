"""
Milestone 1 integration gate test.

End-to-end: real conversation export → real Groq extraction → real BGE embedding
→ SQLite with propositions + embeddings → similarity search returns results.

This test hits real external services (Groq API, sentence-transformers model).
Skipped automatically if GROQ_API_KEY is not set.

Run explicitly:
    cd backend && python -m pytest tests/test_milestone1.py -v
"""

import os
from pathlib import Path

import numpy as np
import pytest
from dotenv import load_dotenv

# Load .env so GROQ_API_KEY is visible to os.getenv
load_dotenv()

# Skip entire module if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping integration test",
)

from services.parser import ConversationParser
from services.storage.sqlite_storage import SQLiteStorage
from services.embedding.bge import BGEBaseEmbedding
from services.extraction import ExtractionService
from services.providers.groq_provider import GroqProvider
from services.ingestion import IngestionService

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "real"
FIXTURE_FILE = FIXTURES_DIR / "Deep Research on Voku Plans.md"
EXPECTED_SESSION_ID = "9a9c2191-84b1-4e48-9906-76509116bc8b"


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def embedder():
    """Real BGE model. scope=module so it loads once for all tests in this file."""
    return BGEBaseEmbedding()


@pytest.fixture
def storage(tmp_path):
    """Fresh SQLite database per test."""
    db = SQLiteStorage(tmp_path / "test_m1.db")
    yield db
    db.close()


@pytest.fixture
def ingestion(storage, embedder):
    """Real pipeline: Groq extraction + BGE embedding + SQLite storage."""
    provider = GroqProvider()
    extraction = ExtractionService(provider)
    return IngestionService(
        storage=storage,
        extraction=extraction,
        embedder=embedder,
    )


# ── Gate Test ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_m1_real_pipeline(ingestion, storage, embedder):
    """
    Milestone 1 gate: real services, real data, real retrieval.

    Proves:
    1. Parser handles real Claude Exporter file
    2. Groq extracts propositions from real conversational text
    3. BGE embeds those propositions into 768-dim vectors
    4. SQLite stores everything with correct provenance
    5. Similarity search returns relevant results
    """

    # ── 1. Parse real conversation ────────────────────────────────────
    parser = ConversationParser()
    all_messages = parser.parse_file(FIXTURE_FILE)

    assert len(all_messages) > 0, "Parser returned no messages"

    user_messages = [m for m in all_messages if m.speaker == "user"]
    assert len(user_messages) >= 2, "Need at least 2 user messages for test"

    # Verify parser extracted correct metadata
    assert all_messages[0].session_id == EXPECTED_SESSION_ID
    assert all_messages[0].source_file == FIXTURE_FILE.name

    # ── 2. Ingest first 2 user messages (keeps test fast) ────────────
    #    Each message = 1 Groq API call (~1-3s) + embedding (~50-200ms)
    first_two_user = [m for m in all_messages if m.speaker == "user"][:2]

    # Build a minimal message list preserving speaker order for ingest_conversation
    # (it filters to user only internally, but we pass what we have)
    result = await ingestion.ingest_conversation(first_two_user)

    # ── 3. Assert: propositions were extracted and stored ─────────────
    assert result.total_propositions_extracted > 0, (
        "Groq extraction returned 0 propositions — check extraction prompt or API"
    )
    assert result.total_propositions_stored > 0, (
        "Propositions extracted but none stored — possible dedup false positive"
    )
    assert result.sessions_processed == 1

    # ── 4. Assert: provenance is correct in SQLite ────────────────────
    stored = storage.find_by_session(EXPECTED_SESSION_ID)
    assert len(stored) == result.total_propositions_stored

    for prop in stored:
        # Every proposition should trace back to the source
        assert prop.session_id == EXPECTED_SESSION_ID
        assert prop.source_file == FIXTURE_FILE.name
        assert prop.node_type in {"belief", "observation", "pattern", "intention", "decision"}
        assert 0.0 <= prop.confidence <= 1.0
        assert prop.text.strip() != ""

    # ── 5. Assert: embeddings exist for all stored propositions ───────
    ids, matrix = storage.get_all_embeddings()
    assert len(ids) == result.total_propositions_stored, (
        f"Embedding count ({len(ids)}) != proposition count ({result.total_propositions_stored})"
    )
    assert matrix.shape == (len(ids), 768), (
        f"Expected shape ({len(ids)}, 768), got {matrix.shape}"
    )

    # ── 6. Assert: similarity search works on real embeddings ─────────
    #    Embed a query related to the conversation topic, verify results come back.
    #    This fixture is "Deep Research on Voku Plans" — so a Voku-related query
    #    should surface propositions.
    query_embedding = embedder.embed("personal knowledge graph temporal tracking")
    similar = storage.find_similar(query_embedding, threshold=0.3, limit=5)

    assert len(similar) > 0, (
        "Similarity search returned 0 results — embeddings may not be stored correctly"
    )
    # Verify the results are actual StoredProposition objects with scores
    for result in similar:
        assert result.proposition.text.strip() != ""
        assert 0.0 <= result.score <= 1.0
