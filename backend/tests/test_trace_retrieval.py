"""
Tests for v2 trace retrieval service.

Uses a mock embedder to return controlled vectors — no model loading needed.
Tests verify ranking behavior (similarity, recency, blending) not embedding quality.
"""

import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace
from services.trace_retrieval import (
    TraceRetrievalService,
    TraceRetrievalResult,
    compute_recency,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


class FakeEmbedder:
    """Returns a predetermined vector for any input.

    Set .next_vector before calling embed() to control what's returned.
    """

    def __init__(self):
        self.next_vector = np.ones(768, dtype=np.float32)
        self.model_name = "fake-embedder"

    def embed(self, text: str) -> np.ndarray:
        return self.next_vector.copy()


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
def embedder():
    return FakeEmbedder()


@pytest.fixture
def retrieval(storage, embedder):
    return TraceRetrievalService(storage, embedder)


def make_trace(
    content: str = "test trace",
    source: str = "user",
    conversation_id: str = "conv-001",
    timestamp: str | None = None,
) -> Trace:
    return Trace(
        id=str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        content=content,
        conversation_id=conversation_id,
        source=source,
    )


def random_embedding(dims: int = 768) -> np.ndarray:
    vec = np.random.randn(dims).astype(np.float32)
    return vec / (np.linalg.norm(vec) + 1e-10)


# ------------------------------------------------------------------
# Recency function (unit tests — no storage needed)
# ------------------------------------------------------------------


class TestComputeRecency:
    def test_now_returns_one(self):
        now = datetime.now(timezone.utc)
        score = compute_recency(now.isoformat(), now)
        assert abs(score - 1.0) < 0.01

    def test_half_life_returns_half(self):
        now = datetime.now(timezone.utc)
        thirty_days_ago = (now - timedelta(days=30)).isoformat()
        score = compute_recency(thirty_days_ago, now, half_life_days=30.0)
        assert abs(score - 0.5) < 0.01

    def test_double_half_life_returns_quarter(self):
        now = datetime.now(timezone.utc)
        sixty_days_ago = (now - timedelta(days=60)).isoformat()
        score = compute_recency(sixty_days_ago, now, half_life_days=30.0)
        assert abs(score - 0.25) < 0.01

    def test_unparseable_returns_default(self):
        now = datetime.now(timezone.utc)
        assert compute_recency("not-a-date", now) == 0.5

    def test_none_returns_default(self):
        now = datetime.now(timezone.utc)
        assert compute_recency(None, now) == 0.5

    def test_future_returns_one(self):
        now = datetime.now(timezone.utc)
        future = (now + timedelta(days=1)).isoformat()
        assert compute_recency(future, now) == 1.0


# ------------------------------------------------------------------
# Retrieval
# ------------------------------------------------------------------


class TestRetrieve:
    def test_basic_retrieval_returns_results(self, storage, embedder, retrieval):
        """Store traces with similar embeddings, verify retrieval returns them."""
        base_vec = np.ones(768, dtype=np.float32)

        t1 = make_trace(content="I love rowing")
        t2 = make_trace(content="Rowing is great")
        storage.store_trace(t1)
        storage.store_trace(t2)

        # Embeddings close to base_vec
        storage.store_embedding(
            t1.id, base_vec + np.random.randn(768).astype(np.float32) * 0.05, "test"
        )
        storage.store_embedding(
            t2.id, base_vec + np.random.randn(768).astype(np.float32) * 0.05, "test"
        )

        # Query with base_vec
        embedder.next_vector = base_vec
        results = retrieval.retrieve("rowing", limit=10, similarity_threshold=0.5)

        assert len(results) == 2
        assert all(isinstance(r, TraceRetrievalResult) for r in results)

    def test_results_sorted_by_combined_score(self, storage, embedder, retrieval):
        """Results are ordered by combined score descending."""
        base_vec = np.ones(768, dtype=np.float32)

        t1 = make_trace(content="First")
        t2 = make_trace(content="Second")
        storage.store_trace(t1)
        storage.store_trace(t2)

        storage.store_embedding(t1.id, base_vec * 0.9, "test")
        storage.store_embedding(t2.id, base_vec * 0.8, "test")

        embedder.next_vector = base_vec
        results = retrieval.retrieve("query", similarity_threshold=0.0)

        assert results[0].combined >= results[1].combined

    def test_temporal_weight_zero_is_pure_similarity(self, storage, embedder, retrieval):
        """With temporal_weight=0, ranking is purely by cosine similarity."""
        now = datetime.now(timezone.utc)

        # t1: old but very similar
        t1 = make_trace(
            content="Old similar",
            timestamp=(now - timedelta(days=90)).isoformat(),
        )
        # t2: recent but less similar
        t2 = make_trace(
            content="New less similar",
            timestamp=now.isoformat(),
        )
        storage.store_trace(t1)
        storage.store_trace(t2)

        close_vec = np.ones(768, dtype=np.float32)
        far_vec = np.ones(768, dtype=np.float32) * 0.5 + np.random.randn(768).astype(np.float32) * 0.3

        storage.store_embedding(t1.id, close_vec, "test")
        storage.store_embedding(t2.id, far_vec, "test")

        embedder.next_vector = close_vec
        results = retrieval.retrieve(
            "query", temporal_weight=0.0, similarity_threshold=0.0
        )

        # Old-but-similar should rank first with pure similarity
        assert results[0].trace.id == t1.id
        assert results[0].similarity > results[1].similarity

    def test_high_temporal_weight_favors_recent(self, storage, embedder, retrieval):
        """With high temporal_weight, recent traces rank higher."""
        now = datetime.now(timezone.utc)
        base_vec = np.ones(768, dtype=np.float32)

        # t1: 90 days old
        t1 = make_trace(
            content="Old trace",
            timestamp=(now - timedelta(days=90)).isoformat(),
        )
        # t2: just now
        t2 = make_trace(
            content="Recent trace",
            timestamp=now.isoformat(),
        )
        storage.store_trace(t1)
        storage.store_trace(t2)

        # Same embedding for both — similarity is equal
        storage.store_embedding(t1.id, base_vec, "test")
        storage.store_embedding(t2.id, base_vec, "test")

        embedder.next_vector = base_vec
        results = retrieval.retrieve(
            "query", temporal_weight=0.8, similarity_threshold=0.0
        )

        # Recent trace wins when temporal weight is high
        assert results[0].trace.id == t2.id
        assert results[0].recency > results[1].recency

    def test_threshold_filters_dissimilar(self, storage, embedder, retrieval):
        """Traces below similarity threshold are excluded."""
        t1 = make_trace(content="Relevant")
        t2 = make_trace(content="Irrelevant")
        storage.store_trace(t1)
        storage.store_trace(t2)

        close_vec = np.ones(768, dtype=np.float32)
        far_vec = -np.ones(768, dtype=np.float32)

        storage.store_embedding(t1.id, close_vec, "test")
        storage.store_embedding(t2.id, far_vec, "test")

        embedder.next_vector = close_vec
        results = retrieval.retrieve("query", similarity_threshold=0.5)

        assert len(results) == 1
        assert results[0].trace.id == t1.id

    def test_limit_caps_results(self, storage, embedder, retrieval):
        """Limit parameter caps the number of returned results."""
        base_vec = np.ones(768, dtype=np.float32)

        for i in range(10):
            t = make_trace(content=f"Trace {i}")
            storage.store_trace(t)
            storage.store_embedding(t.id, base_vec, "test")

        embedder.next_vector = base_vec
        results = retrieval.retrieve("query", limit=3, similarity_threshold=0.0)

        assert len(results) <= 3

    def test_empty_database_returns_empty(self, storage, embedder, retrieval):
        """No traces/embeddings returns empty list, not an error."""
        embedder.next_vector = np.ones(768, dtype=np.float32)
        results = retrieval.retrieve("any query")
        assert results == []

    def test_result_has_scoring_breakdown(self, storage, embedder, retrieval):
        """Each result exposes similarity, recency, and combined scores."""
        base_vec = np.ones(768, dtype=np.float32)
        t = make_trace(content="Test trace")
        storage.store_trace(t)
        storage.store_embedding(t.id, base_vec, "test")

        embedder.next_vector = base_vec
        results = retrieval.retrieve("query", similarity_threshold=0.0)

        assert len(results) == 1
        r = results[0]
        assert 0.0 <= r.similarity <= 1.0
        assert 0.0 <= r.recency <= 1.0
        assert 0.0 <= r.combined <= 1.0

    def test_retrieves_both_user_and_assistant_traces(self, storage, embedder, retrieval):
        """Both user and assistant traces are retrievable."""
        base_vec = np.ones(768, dtype=np.float32)

        t_user = make_trace(content="User message", source="user")
        t_asst = make_trace(content="Assistant response", source="assistant")
        storage.store_trace(t_user)
        storage.store_trace(t_asst)

        storage.store_embedding(t_user.id, base_vec, "test")
        storage.store_embedding(t_asst.id, base_vec, "test")

        embedder.next_vector = base_vec
        results = retrieval.retrieve("query", similarity_threshold=0.0)

        sources = {r.trace.source for r in results}
        assert "user" in sources
        assert "assistant" in sources
