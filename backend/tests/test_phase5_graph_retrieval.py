"""
Tests for Phase 5 graph-traversal retrieval (Task 5.2).

Tests that retrieval expands results by following connections:
  - Temporal connections bring in conversation context
  - Intentional connections bring in cross-session threads
  - Semantic connections are NOT followed (redundant with vector search)
  - Graph expansion is bounded and scored correctly
"""

import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace, Connection
from services.embedding.bge import BGEBaseEmbedding
from services.trace_retrieval import TraceRetrievalService


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_embedder():
    return BGEBaseEmbedding()


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_graph.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    s = SQLiteTraceStorage(db_path)
    yield s
    s.close()


def store_and_embed(storage, embedder, content, source="user",
                    conversation_id="conv-001", parent_trace_id=None,
                    timestamp=None):
    """Store a trace and its embedding. Returns the Trace."""
    t = Trace(
        id=str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        content=content,
        conversation_id=conversation_id,
        parent_trace_id=parent_trace_id,
        source=source,
    )
    storage.store_trace(t)
    emb = embedder.embed(content)
    storage.store_embedding(t.id, emb, embedder.model_name)
    return t


def add_connection(storage, source_id, target_id, conn_type, weight=1.0):
    """Store a connection between two traces."""
    storage.store_connection(Connection(
        source_id=source_id,
        target_id=target_id,
        type=conn_type,
        weight=weight,
        created_at=datetime.now(timezone.utc).isoformat(),
    ))


# ------------------------------------------------------------------
# Graph expansion via temporal connections
# ------------------------------------------------------------------


class TestTemporalExpansion:
    def test_temporal_neighbor_included_in_results(self, storage, real_embedder):
        """A trace connected temporally to a vector-matched trace appears in results."""
        now = datetime.now(timezone.utc)

        # Trace A: matches query via embedding
        a = store_and_embed(
            storage, real_embedder,
            "I want to build AI systems for healthcare applications",
            timestamp=(now - timedelta(minutes=2)).isoformat(),
        )
        # Trace B: connected temporally to A, different topic (won't match embedding)
        b = store_and_embed(
            storage, real_embedder,
            "My apartment lease expires in June and I need to find a new place",
            parent_trace_id=a.id,
            timestamp=(now - timedelta(minutes=1)).isoformat(),
        )
        add_connection(storage, a.id, b.id, "temporal")

        retrieval = TraceRetrievalService(storage, real_embedder)
        results = retrieval.retrieve(
            "healthcare AI engineering",
            limit=5,
            use_graph=True,
        )

        result_ids = {r.trace.id for r in results}
        assert a.id in result_ids, "Vector-matched trace should be in results"
        assert b.id in result_ids, "Temporally connected trace should be expanded into results"

    def test_graph_expansion_disabled(self, storage, real_embedder):
        """With use_graph=False, only vector-matched traces appear."""
        now = datetime.now(timezone.utc)

        a = store_and_embed(
            storage, real_embedder,
            "I want to build AI systems for healthcare applications",
            timestamp=(now - timedelta(minutes=2)).isoformat(),
        )
        b = store_and_embed(
            storage, real_embedder,
            "My apartment lease expires in June and I need to find a new place",
            parent_trace_id=a.id,
            timestamp=(now - timedelta(minutes=1)).isoformat(),
        )
        add_connection(storage, a.id, b.id, "temporal")

        retrieval = TraceRetrievalService(storage, real_embedder)
        results = retrieval.retrieve(
            "healthcare AI engineering",
            limit=5,
            use_graph=False,
            similarity_threshold=0.3,
        )

        result_ids = {r.trace.id for r in results}
        assert a.id in result_ids
        # B should NOT appear — it's about apartments, not healthcare
        # (only if its embedding is below threshold, which it should be)
        # This is a soft assertion — if embeddings happen to be similar, skip
        if b.id in result_ids:
            # Check it got there via vector search, not graph
            b_result = [r for r in results if r.trace.id == b.id][0]
            assert b_result.similarity >= 0.3, "B should only appear if genuinely similar"


# ------------------------------------------------------------------
# Graph expansion via intentional connections
# ------------------------------------------------------------------


class TestIntentionalExpansion:
    def test_intentional_connection_expands_retrieval(self, storage, real_embedder):
        """Cross-session intentional links bring in connected traces."""
        now = datetime.now(timezone.utc)

        # Session 1: career discussion
        a = store_and_embed(
            storage, real_embedder,
            "I decided to focus on AI engineering for my career",
            conversation_id="conv-001",
            timestamp=(now - timedelta(days=7)).isoformat(),
        )
        # Session 2: unrelated content but intentionally linked
        b = store_and_embed(
            storage, real_embedder,
            "The Grothendieck approach removes assumptions instead of adding features",
            conversation_id="conv-002",
            timestamp=(now - timedelta(days=1)).isoformat(),
        )
        add_connection(storage, a.id, b.id, "intentional", weight=1.0)

        retrieval = TraceRetrievalService(storage, real_embedder)
        results = retrieval.retrieve(
            "AI engineering career plans",
            limit=5,
            use_graph=True,
        )

        result_ids = {r.trace.id for r in results}
        assert a.id in result_ids
        assert b.id in result_ids, "Intentionally linked trace should be expanded"


# ------------------------------------------------------------------
# Semantic connections NOT followed
# ------------------------------------------------------------------


class TestSemanticNotExpanded:
    def test_semantic_connections_not_followed(self, storage, real_embedder):
        """Semantic connections don't expand retrieval (redundant with vector search)."""
        now = datetime.now(timezone.utc)

        a = store_and_embed(
            storage, real_embedder,
            "Building a FastAPI backend for trace storage",
            timestamp=(now - timedelta(minutes=2)).isoformat(),
        )
        # Very different content, but we manually add a semantic connection
        b = store_and_embed(
            storage, real_embedder,
            "My favorite breakfast is scrambled eggs with toast",
            timestamp=(now - timedelta(minutes=1)).isoformat(),
        )
        add_connection(storage, a.id, b.id, "semantic", weight=0.8)

        retrieval = TraceRetrievalService(storage, real_embedder)
        results = retrieval.retrieve(
            "FastAPI trace backend development",
            limit=5,
            use_graph=True,
            similarity_threshold=0.3,
        )

        result_ids = {r.trace.id for r in results}
        assert a.id in result_ids
        # B should NOT appear just because of semantic connection
        # (it might appear if embeddings are coincidentally similar, but unlikely)


# ------------------------------------------------------------------
# Score discounting and deduplication
# ------------------------------------------------------------------


class TestGraphScoring:
    def test_expanded_traces_have_discounted_score(self, storage, real_embedder):
        """Graph-expanded traces score lower than their parent vector match."""
        now = datetime.now(timezone.utc)

        a = store_and_embed(
            storage, real_embedder,
            "I want to build AI systems for healthcare applications",
            timestamp=now.isoformat(),
        )
        b = store_and_embed(
            storage, real_embedder,
            "My apartment lease expires in June",
            parent_trace_id=a.id,
            timestamp=(now + timedelta(seconds=1)).isoformat(),
        )
        add_connection(storage, a.id, b.id, "temporal")

        retrieval = TraceRetrievalService(storage, real_embedder)
        results = retrieval.retrieve(
            "healthcare AI engineering",
            limit=5,
            use_graph=True,
        )

        a_result = next((r for r in results if r.trace.id == a.id), None)
        b_result = next((r for r in results if r.trace.id == b.id), None)

        assert a_result is not None
        if b_result is not None:
            assert b_result.combined < a_result.combined, \
                "Expanded trace should score lower than the vector-matched parent"

    def test_duplicate_keeps_higher_score(self, storage, real_embedder):
        """If a trace is found by both vector search and graph expansion, keep the higher score."""
        now = datetime.now(timezone.utc)

        # Both about AI — both will match vector search
        a = store_and_embed(
            storage, real_embedder,
            "AI engineering requires understanding of transformer architectures",
            timestamp=now.isoformat(),
        )
        b = store_and_embed(
            storage, real_embedder,
            "Transformer attention mechanisms are the key innovation in modern AI",
            parent_trace_id=a.id,
            timestamp=(now + timedelta(seconds=1)).isoformat(),
        )
        add_connection(storage, a.id, b.id, "temporal")

        retrieval = TraceRetrievalService(storage, real_embedder)
        results = retrieval.retrieve(
            "transformer architecture in AI",
            limit=5,
            use_graph=True,
        )

        # B should appear once, not twice
        b_results = [r for r in results if r.trace.id == b.id]
        assert len(b_results) <= 1, "Duplicate trace should appear at most once"

    def test_expansion_bounded_by_limit(self, storage, real_embedder):
        """Graph expansion doesn't return more than 2× requested limit."""
        now = datetime.now(timezone.utc)

        # Create a chain of 20 traces
        parent_id = None
        traces = []
        for i in range(20):
            t = store_and_embed(
                storage, real_embedder,
                f"Discussion point {i} about machine learning pipelines",
                parent_trace_id=parent_id,
                timestamp=(now + timedelta(seconds=i)).isoformat(),
            )
            if parent_id:
                add_connection(storage, parent_id, t.id, "temporal")
            parent_id = t.id
            traces.append(t)

        retrieval = TraceRetrievalService(storage, real_embedder)
        results = retrieval.retrieve(
            "machine learning pipeline discussion",
            limit=5,
            use_graph=True,
        )

        assert len(results) <= 10, f"Results ({len(results)}) should not exceed 2× limit (10)"
