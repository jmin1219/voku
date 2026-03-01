"""
Tests for connection computation service.

Tests temporal and semantic connection generation from stored traces.
Uses real embeddings for semantic tests (verifies similar traces connect).
"""

import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace
from services.connections import ConnectionService


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test.db"
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    db = SQLiteTraceStorage(db_path)
    yield db
    db.close()


@pytest.fixture
def service(storage):
    return ConnectionService(storage)


def make_trace(
    content: str = "test",
    source: str = "user",
    conversation_id: str = "conv-001",
    parent_trace_id: str | None = None,
    timestamp: str | None = None,
) -> Trace:
    return Trace(
        id=str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        content=content,
        conversation_id=conversation_id,
        parent_trace_id=parent_trace_id,
        source=source,
    )


def random_embedding(dims: int = 768) -> np.ndarray:
    vec = np.random.randn(dims).astype(np.float32)
    return vec / (np.linalg.norm(vec) + 1e-10)


# ------------------------------------------------------------------
# Temporal connections
# ------------------------------------------------------------------


class TestTemporalConnections:
    def test_creates_connections_from_parent_links(self, storage, service):
        """Parent → child links become temporal connections."""
        t1 = make_trace(content="First message")
        storage.store_trace(t1)

        t2 = make_trace(content="Second message", parent_trace_id=t1.id)
        storage.store_trace(t2)

        t3 = make_trace(content="Third message", parent_trace_id=t2.id)
        storage.store_trace(t3)

        count = service.compute_temporal_connections()
        assert count == 2

        conns = storage.get_connections_by_type("temporal")
        assert len(conns) == 2

        # Check directionality: parent → child
        sources = {c.source_id for c in conns}
        targets = {c.target_id for c in conns}
        assert t1.id in sources
        assert t2.id in sources
        assert t2.id in targets
        assert t3.id in targets

    def test_temporal_connections_weight_is_one(self, storage, service):
        """All temporal connections have weight 1.0."""
        t1 = make_trace(content="A")
        storage.store_trace(t1)
        t2 = make_trace(content="B", parent_trace_id=t1.id)
        storage.store_trace(t2)

        service.compute_temporal_connections()
        conns = storage.get_connections_by_type("temporal")
        assert all(c.weight == 1.0 for c in conns)

    def test_no_parent_means_no_connection(self, storage, service):
        """Root traces (no parent) don't generate connections."""
        t1 = make_trace(content="Root trace")
        storage.store_trace(t1)

        count = service.compute_temporal_connections()
        assert count == 0

    def test_idempotent_recomputation(self, storage, service):
        """Running twice produces the same result (clears then recreates)."""
        t1 = make_trace(content="A")
        storage.store_trace(t1)
        t2 = make_trace(content="B", parent_trace_id=t1.id)
        storage.store_trace(t2)

        service.compute_temporal_connections()
        service.compute_temporal_connections()

        conns = storage.get_connections_by_type("temporal")
        assert len(conns) == 1

    def test_multiple_conversations(self, storage, service):
        """Temporal connections span across multiple conversations."""
        # Conv 1: 2 messages
        t1 = make_trace(content="Conv1 msg1", conversation_id="conv-A")
        storage.store_trace(t1)
        t2 = make_trace(content="Conv1 msg2", conversation_id="conv-A", parent_trace_id=t1.id)
        storage.store_trace(t2)

        # Conv 2: 3 messages
        t3 = make_trace(content="Conv2 msg1", conversation_id="conv-B")
        storage.store_trace(t3)
        t4 = make_trace(content="Conv2 msg2", conversation_id="conv-B", parent_trace_id=t3.id)
        storage.store_trace(t4)
        t5 = make_trace(content="Conv2 msg3", conversation_id="conv-B", parent_trace_id=t4.id)
        storage.store_trace(t5)

        count = service.compute_temporal_connections()
        assert count == 3  # 1 from conv-A + 2 from conv-B


# ------------------------------------------------------------------
# Semantic connections
# ------------------------------------------------------------------


class TestSemanticConnections:
    def test_creates_knn_connections(self, storage, service):
        """Traces with similar embeddings get connected."""
        # Create 3 traces with embeddings
        base_vec = np.ones(768, dtype=np.float32)
        for i in range(3):
            t = make_trace(content=f"Trace {i}")
            storage.store_trace(t)
            emb = base_vec + np.random.randn(768).astype(np.float32) * 0.05
            storage.store_embedding(t.id, emb, "test")

        count = service.compute_semantic_connections(k=2, threshold=0.3)
        assert count > 0

        conns = storage.get_connections_by_type("semantic")
        assert len(conns) > 0
        assert all(c.type == "semantic" for c in conns)

    def test_semantic_weights_are_similarity_scores(self, storage, service):
        """Connection weights reflect actual cosine similarity."""
        t1 = make_trace(content="A")
        t2 = make_trace(content="B")
        storage.store_trace(t1)
        storage.store_trace(t2)

        # Very similar embeddings
        v1 = np.ones(768, dtype=np.float32)
        v2 = np.ones(768, dtype=np.float32) * 0.99
        storage.store_embedding(t1.id, v1, "test")
        storage.store_embedding(t2.id, v2, "test")

        service.compute_semantic_connections(k=5, threshold=0.0)
        conns = storage.get_connections_by_type("semantic")

        assert len(conns) == 1
        assert conns[0].weight > 0.9  # Very similar vectors

    def test_threshold_filters_dissimilar(self, storage, service):
        """Traces below threshold don't get connected."""
        t1 = make_trace(content="A")
        t2 = make_trace(content="B")
        storage.store_trace(t1)
        storage.store_trace(t2)

        # Opposite embeddings
        v1 = np.ones(768, dtype=np.float32)
        v2 = -np.ones(768, dtype=np.float32)
        storage.store_embedding(t1.id, v1, "test")
        storage.store_embedding(t2.id, v2, "test")

        count = service.compute_semantic_connections(k=5, threshold=0.5)
        assert count == 0

    def test_idempotent_recomputation(self, storage, service):
        """Running twice produces the same result."""
        base = np.ones(768, dtype=np.float32)
        for i in range(4):
            t = make_trace(content=f"T{i}")
            storage.store_trace(t)
            storage.store_embedding(t.id, base + np.random.randn(768).astype(np.float32) * 0.05, "test")

        count1 = service.compute_semantic_connections(k=2, threshold=0.3)
        count2 = service.compute_semantic_connections(k=2, threshold=0.3)
        assert count1 == count2

    def test_fewer_traces_than_k(self, storage, service):
        """Works correctly when fewer traces exist than k neighbors."""
        t1 = make_trace(content="Only one")
        storage.store_trace(t1)
        storage.store_embedding(t1.id, random_embedding(), "test")

        # k=5 but only 1 trace — should not crash
        count = service.compute_semantic_connections(k=5, threshold=0.0)
        assert count == 0  # Can't connect to self

    def test_deduplicates_bidirectional(self, storage, service):
        """A→B and B→A are stored as one connection (smaller ID first)."""
        t1 = make_trace(content="Alpha")
        t2 = make_trace(content="Beta")
        storage.store_trace(t1)
        storage.store_trace(t2)

        vec = np.ones(768, dtype=np.float32)
        storage.store_embedding(t1.id, vec, "test")
        storage.store_embedding(t2.id, vec * 0.99, "test")

        service.compute_semantic_connections(k=5, threshold=0.0)
        conns = storage.get_connections_by_type("semantic")

        # Should be exactly 1, not 2
        assert len(conns) == 1


# ------------------------------------------------------------------
# Compute all
# ------------------------------------------------------------------


class TestComputeAll:
    def test_computes_both_types(self, storage, service):
        """compute_all returns counts for temporal and semantic."""
        t1 = make_trace(content="First")
        storage.store_trace(t1)
        t2 = make_trace(content="Second", parent_trace_id=t1.id)
        storage.store_trace(t2)

        vec = np.ones(768, dtype=np.float32)
        storage.store_embedding(t1.id, vec, "test")
        storage.store_embedding(t2.id, vec * 0.99, "test")

        result = service.compute_all(k=5, threshold=0.0)
        assert "temporal" in result
        assert "semantic" in result
        assert result["temporal"] == 1
        assert result["semantic"] >= 1
