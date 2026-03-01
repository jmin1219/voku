"""
Tests for Phase 5 intention recognition (Task 5.9).

Traces with "intention" or "commitment" annotations get a retrieval
boost, surfacing stated goals when topically relevant.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace, Annotation
from services.trace_retrieval import TraceRetrievalService


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


class FakeEmbedder:
    def __init__(self):
        self.next_vector = np.ones(768, dtype=np.float32)
        self.model_name = "fake-embedder"

    def embed(self, text):
        return self.next_vector.copy()


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_intention.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    s = SQLiteTraceStorage(db_path)
    yield s
    s.close()


@pytest.fixture
def embedder():
    return FakeEmbedder()


def store_trace_with_embedding(storage, embedder, content, source="user"):
    t = Trace(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        content=content,
        conversation_id="conv-001",
        source=source,
    )
    storage.store_trace(t)
    vec = np.ones(768, dtype=np.float32)
    storage.store_embedding(t.id, vec, embedder.model_name)
    return t


def add_annotation(storage, trace_id, ann_type, key="goal", value="test"):
    ann = Annotation(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        type=ann_type,
        key=key,
        value=value,
        confidence=0.9,
        extracted_at=datetime.now(timezone.utc).isoformat(),
        extractor="test",
    )
    storage.store_annotation(ann)


class TestIntentionBoost:
    def test_intention_trace_scores_higher(self, storage, embedder):
        """Trace with 'intention' annotation scores higher than identical trace without."""
        t_intention = store_trace_with_embedding(storage, embedder, "Goal trace")
        add_annotation(storage, t_intention.id, "intention", "career", "pursue AI")

        t_plain = store_trace_with_embedding(storage, embedder, "Plain trace")
        add_annotation(storage, t_plain.id, "topic", "misc", "stuff")

        retrieval = TraceRetrievalService(storage, embedder)
        embedder.next_vector = np.ones(768, dtype=np.float32)
        results = retrieval.retrieve("query", limit=10, similarity_threshold=0.0, use_graph=False)

        scores = {r.trace.id: r.combined for r in results}
        assert scores[t_intention.id] > scores[t_plain.id], \
            "Intention trace should score higher"

    def test_commitment_trace_scores_higher(self, storage, embedder):
        """Trace with 'commitment' annotation also gets the boost."""
        t_commit = store_trace_with_embedding(storage, embedder, "Commitment trace")
        add_annotation(storage, t_commit.id, "commitment", "demo", "ship by March 31")

        t_plain = store_trace_with_embedding(storage, embedder, "Normal trace")
        add_annotation(storage, t_plain.id, "topic", "misc", "stuff")

        retrieval = TraceRetrievalService(storage, embedder)
        embedder.next_vector = np.ones(768, dtype=np.float32)
        results = retrieval.retrieve("query", limit=10, similarity_threshold=0.0, use_graph=False)

        scores = {r.trace.id: r.combined for r in results}
        assert scores[t_commit.id] > scores[t_plain.id]

    def test_boost_configurable(self, storage, embedder):
        """intention_boost parameter controls the multiplier."""
        t = store_trace_with_embedding(storage, embedder, "Goal trace")
        add_annotation(storage, t.id, "intention", "test", "test")

        retrieval = TraceRetrievalService(storage, embedder)
        embedder.next_vector = np.ones(768, dtype=np.float32)

        results_default = retrieval.retrieve(
            "query", limit=10, similarity_threshold=0.0,
            use_graph=False, intention_boost=1.3,
        )
        results_high = retrieval.retrieve(
            "query", limit=10, similarity_threshold=0.0,
            use_graph=False, intention_boost=2.0,
        )

        score_default = next(r.combined for r in results_default if r.trace.id == t.id)
        score_high = next(r.combined for r in results_high if r.trace.id == t.id)
        assert score_high > score_default

    def test_non_intention_unaffected(self, storage, embedder):
        """Traces with other annotation types don't get boosted."""
        t_topic = store_trace_with_embedding(storage, embedder, "Topic trace")
        add_annotation(storage, t_topic.id, "topic", "cooking", "sourdough")

        t_bare = store_trace_with_embedding(storage, embedder, "Bare trace")

        retrieval = TraceRetrievalService(storage, embedder)
        embedder.next_vector = np.ones(768, dtype=np.float32)
        results = retrieval.retrieve("query", limit=10, similarity_threshold=0.0, use_graph=False)

        scores = {r.trace.id: r.combined for r in results}
        # topic annotation should NOT boost
        assert abs(scores.get(t_topic.id, 0) - scores.get(t_bare.id, 0)) < 0.01
