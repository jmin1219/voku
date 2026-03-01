"""
End-to-end tests for v2 trace pipeline.

Tests the full vertical slice: store → embed → retrieve → assemble,
including cross-session retrieval quality and API endpoint behavior.

Uses real BGE embeddings (no mocks) for retrieval quality tests.
The embedding model loads once per test session (~2s).
"""

import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace
from services.embedding.bge import BGEBaseEmbedding
from services.trace_retrieval import TraceRetrievalService
from services.trace_context import TraceContextAssembly


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


@pytest.fixture(scope="module")
def real_embedder():
    """Load the real BGE embedder once for the module (expensive)."""
    return BGEBaseEmbedding()


@pytest.fixture
def seeded_storage(tmp_path, real_embedder):
    """Storage pre-populated with a two-session conversation arc.

    Session 1 (7 days ago): Career discussion — AI vs data science.
    Session 2 (just now): Technical architecture discussion.

    This tests whether Session 2 retrieval surfaces Session 1 context.
    """
    db_path = tmp_path / "e2e.db"
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()

    storage = SQLiteTraceStorage(db_path)
    now = datetime.now(timezone.utc)

    # Session 1: career discussion (7 days ago)
    session1_messages = [
        ("user", "I want to transition from data science to AI engineering. My background is in neuroscience."),
        ("assistant", "Your neuroscience background is an asset for AI engineering, especially in areas like cognitive AI and human-AI interaction."),
        ("user", "I'm worried about the gap in my systems programming skills. Most AI engineer job postings want distributed systems experience."),
        ("assistant", "That's a common concern. Focus on building a strong portfolio project that demonstrates system design thinking rather than trying to check every box."),
    ]
    parent_id = None
    for i, (role, content) in enumerate(session1_messages):
        t = Trace(
            id=str(uuid.uuid4()),
            timestamp=(now - timedelta(days=7, seconds=-i * 30)).isoformat(),
            content=content,
            conversation_id="e2e-conv-001",
            parent_trace_id=parent_id,
            source=role,
        )
        storage.store_trace(t)
        emb = real_embedder.embed(content)
        storage.store_embedding(t.id, emb, real_embedder.model_name)
        parent_id = t.id

    # Session 2: technical discussion (just now)
    session2_messages = [
        ("user", "I'm building a trace-based knowledge graph. Every conversation becomes immutable timestamped traces."),
        ("assistant", "Immutable traces with temporal anchoring is a strong foundation. How are you handling retrieval?"),
    ]
    parent_id = None
    for i, (role, content) in enumerate(session2_messages):
        t = Trace(
            id=str(uuid.uuid4()),
            timestamp=(now - timedelta(seconds=60 - i * 30)).isoformat(),
            content=content,
            conversation_id="e2e-conv-002",
            parent_trace_id=parent_id,
            source=role,
        )
        storage.store_trace(t)
        emb = real_embedder.embed(content)
        storage.store_embedding(t.id, emb, real_embedder.model_name)
        parent_id = t.id

    yield storage
    storage.close()


@pytest.fixture
def retrieval(seeded_storage, real_embedder):
    return TraceRetrievalService(seeded_storage, real_embedder)


@pytest.fixture
def assembly(retrieval):
    return TraceContextAssembly(retrieval)


# ------------------------------------------------------------------
# Cross-session retrieval quality
# ------------------------------------------------------------------


class TestCrossSessionRetrieval:
    """The core thesis: accumulated traces improve future conversations."""

    def test_career_query_retrieves_session1(self, retrieval):
        """A career question in Session 2 should surface Session 1 career traces."""
        results = retrieval.retrieve(
            "What are my career goals in AI?",
            limit=5,
            similarity_threshold=0.3,
        )

        assert len(results) > 0
        contents = [r.trace.content.lower() for r in results]
        # Should find the career discussion from Session 1
        career_found = any(
            "data science" in c or "ai engineering" in c or "neuroscience" in c
            for c in contents
        )
        assert career_found, f"Career traces not found. Got: {contents[:3]}"

    def test_technical_query_retrieves_session2(self, retrieval):
        """A technical question should surface Session 2 architecture traces."""
        results = retrieval.retrieve(
            "How does the trace storage work?",
            limit=5,
            similarity_threshold=0.3,
        )

        assert len(results) > 0
        contents = [r.trace.content.lower() for r in results]
        technical_found = any(
            "trace" in c or "immutable" in c or "knowledge graph" in c
            for c in contents
        )
        assert technical_found, f"Technical traces not found. Got: {contents[:3]}"

    def test_retrieval_spans_sessions(self, retrieval):
        """A broad query should retrieve from both sessions."""
        results = retrieval.retrieve(
            "Tell me about my AI project and career plans",
            limit=6,
            similarity_threshold=0.25,
        )

        conv_ids = {r.trace.conversation_id for r in results}
        assert len(conv_ids) >= 2, f"Expected traces from 2+ sessions, got {conv_ids}"

    def test_recency_boosts_recent_session(self, retrieval):
        """With temporal weighting, recent Session 2 traces rank higher than equivalent Session 1 traces."""
        results = retrieval.retrieve(
            "building AI systems",
            limit=6,
            temporal_weight=0.5,
            similarity_threshold=0.25,
        )

        if len(results) >= 2:
            # At least one of the top 2 should be from the recent session
            top2_convs = {results[0].trace.conversation_id, results[1].trace.conversation_id}
            assert "e2e-conv-002" in top2_convs, (
                f"Recent session not in top 2. Got: {[r.trace.conversation_id for r in results[:3]]}"
            )


# ------------------------------------------------------------------
# Context assembly integration
# ------------------------------------------------------------------


class TestContextAssemblyIntegration:
    """Full pipeline: retrieval → formatted system prompt."""

    def test_assembles_prompt_with_cross_session_context(self, assembly):
        """System prompt includes traces from prior sessions."""
        prompt, ids = assembly.build_system_prompt(
            "What should I focus on for my AI career?"
        )

        assert prompt is not None
        assert len(ids) > 0
        assert "Voku" in prompt
        assert "[1]" in prompt

    def test_prompt_trace_ids_match_storage(self, assembly, seeded_storage):
        """Every trace ID in the prompt exists in storage."""
        _, ids = assembly.build_system_prompt("AI engineering career")

        for trace_id in ids:
            trace = seeded_storage.get_trace(trace_id)
            assert trace is not None, f"Trace {trace_id} not found in storage"


# ------------------------------------------------------------------
# History endpoint behavior
# ------------------------------------------------------------------


class TestHistoryFormat:
    """Verify the data format that /history would return."""

    def test_list_conversations_returns_both_sessions(self, seeded_storage):
        convs = seeded_storage.list_conversations()
        assert len(convs) == 2

    def test_conversations_ordered_by_recency(self, seeded_storage):
        convs = seeded_storage.list_conversations()
        # Most recent first
        assert convs[0]["id"] == "e2e-conv-002"
        assert convs[1]["id"] == "e2e-conv-001"

    def test_conversation_trace_count(self, seeded_storage):
        convs = seeded_storage.list_conversations()
        conv_map = {c["id"]: c for c in convs}
        assert conv_map["e2e-conv-001"]["trace_count"] == 4
        assert conv_map["e2e-conv-002"]["trace_count"] == 2

    def test_traces_have_parent_chain(self, seeded_storage):
        """Traces in a conversation form a linked chain via parent_trace_id."""
        traces = seeded_storage.get_traces_by_conversation("e2e-conv-001")
        assert traces[0].parent_trace_id is None  # First message has no parent
        for i in range(1, len(traces)):
            assert traces[i].parent_trace_id == traces[i - 1].id


# ------------------------------------------------------------------
# Trace storage as chat backend
# ------------------------------------------------------------------


class TestTracesAsChatBackend:
    """Verify traces can serve the same role as ConversationService."""

    def test_store_user_and_assistant_traces(self, tmp_path, real_embedder):
        """Simulate what chat.py does: store user trace, embed, store assistant trace, embed."""
        db_path = tmp_path / "chat_sim.db"
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_PATH.read_text())
        conn.close()

        storage = SQLiteTraceStorage(db_path)
        conv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # User message
        user_trace = Trace(
            id=str(uuid.uuid4()),
            timestamp=now.isoformat(),
            content="What should I work on today?",
            conversation_id=conv_id,
            parent_trace_id=None,
            source="user",
        )
        storage.store_trace(user_trace)
        user_emb = real_embedder.embed(user_trace.content)
        storage.store_embedding(user_trace.id, user_emb, real_embedder.model_name)

        # Assistant response
        asst_trace = Trace(
            id=str(uuid.uuid4()),
            timestamp=(now + timedelta(seconds=3)).isoformat(),
            content="Based on your recent focus on the trace pipeline, I'd suggest continuing with the E2E tests.",
            conversation_id=conv_id,
            parent_trace_id=user_trace.id,
            source="assistant",
        )
        storage.store_trace(asst_trace)
        asst_emb = real_embedder.embed(asst_trace.content)
        storage.store_embedding(asst_trace.id, asst_emb, real_embedder.model_name)

        # Verify: conversation exists with 2 traces
        convs = storage.list_conversations()
        assert len(convs) == 1
        assert convs[0]["trace_count"] == 2

        # Verify: traces are threaded
        traces = storage.get_traces_by_conversation(conv_id)
        assert len(traces) == 2
        assert traces[0].source == "user"
        assert traces[1].source == "assistant"
        assert traces[1].parent_trace_id == traces[0].id

        # Verify: both are retrievable via similarity search
        query_emb = real_embedder.embed("work priorities and tasks")
        results = storage.find_similar(query_emb, threshold=0.3, limit=5)
        assert len(results) >= 1

        storage.close()
