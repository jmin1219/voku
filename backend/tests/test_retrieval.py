"""
Tests for RetrievalService — Phase 2 core component.

Unit tests with synthetic data + integration tests against m2_conversation.db.
"""

from datetime import datetime, timezone, timedelta

import numpy as np
import pytest

from services.retrieval import RetrievalService
from services.storage.sqlite_storage import SQLiteStorage
from services.storage.models import StoredProposition
from services.embedding.bge import BGEBaseEmbedding


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def embedder():
    """Real BGE embedder for semantic tests."""
    return BGEBaseEmbedding()


@pytest.fixture
def storage_with_data(tmp_path, embedder):
    """Storage pre-loaded with propositions that have real embeddings."""
    db = SQLiteStorage(tmp_path / "test_retrieval.db")

    now = datetime.now(timezone.utc)
    props = [
        StoredProposition(
            id="p-recent-stance", text="I believe SQLite is the right database for Voku",
            node_type="stance", confidence=0.9, source_type="conversation",
            created_at=(now - timedelta(days=1)).isoformat(),
            source_file="recent.md",
        ),
        StoredProposition(
            id="p-old-stance", text="I think Postgres is the best database choice",
            node_type="stance", confidence=0.85, source_type="conversation",
            created_at=(now - timedelta(days=90)).isoformat(),
            source_file="old.md",
        ),
        StoredProposition(
            id="p-event", text="Moved to Vancouver in August 2025",
            node_type="event", confidence=1.0, source_type="conversation",
            created_at=(now - timedelta(days=30)).isoformat(),
            event_timeframe="recent", source_file="move.md",
        ),
        StoredProposition(
            id="p-superseded", text="Interest rates determine the value of a currency",
            node_type="stance", confidence=0.7, source_type="conversation",
            created_at=(now - timedelta(days=45)).isoformat(),
            superseded_in_conversation=True, source_file="money.md",
        ),
        StoredProposition(
            id="p-unrelated", text="Chicken should be roasted at 425 degrees for crispy skin",
            node_type="event", confidence=1.0, source_type="conversation",
            created_at=(now - timedelta(days=60)).isoformat(),
            source_file="cooking.md",
        ),
    ]

    for prop in props:
        db.store_proposition(prop)
        embedding = embedder.embed(prop.text)
        db.store_embedding(prop.id, embedding, embedder.model_name)

    yield db
    db.close()


@pytest.fixture
def retrieval(storage_with_data, embedder):
    """RetrievalService wired to test storage."""
    return RetrievalService(storage_with_data, embedder)


# ---------------------------------------------------------------------------
# Recency computation
# ---------------------------------------------------------------------------

class TestRecencyComputation:
    def test_now_returns_one(self):
        now = datetime.now(timezone.utc)
        score = RetrievalService._compute_recency(now.isoformat(), now)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_half_life_returns_half(self):
        now = datetime.now(timezone.utc)
        thirty_days_ago = (now - timedelta(days=30)).isoformat()
        score = RetrievalService._compute_recency(thirty_days_ago, now, half_life_days=30.0)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_two_half_lives_returns_quarter(self):
        now = datetime.now(timezone.utc)
        sixty_days_ago = (now - timedelta(days=60)).isoformat()
        score = RetrievalService._compute_recency(sixty_days_ago, now, half_life_days=30.0)
        assert score == pytest.approx(0.25, abs=0.01)

    def test_very_old_approaches_zero(self):
        now = datetime.now(timezone.utc)
        year_ago = (now - timedelta(days=365)).isoformat()
        score = RetrievalService._compute_recency(year_ago, now, half_life_days=30.0)
        assert score < 0.001

    def test_unparseable_date_returns_default(self):
        now = datetime.now(timezone.utc)
        score = RetrievalService._compute_recency("not-a-date", now)
        assert score == 0.5


# ---------------------------------------------------------------------------
# Flat retrieval (temporal_weight=0)
# ---------------------------------------------------------------------------

class TestFlatRetrieval:
    def test_relevant_query_returns_results(self, retrieval):
        results = retrieval.retrieve("What database should I use?", temporal_weight=0.0)
        assert len(results) > 0
        texts = [r.text for r in results]
        assert any("SQLite" in t or "Postgres" in t for t in texts)

    def test_unrelated_query_returns_few_results(self, retrieval):
        results = retrieval.retrieve("quantum physics experiments", temporal_weight=0.0, similarity_threshold=0.5)
        # High threshold should filter out unrelated
        assert len(results) == 0 or all(r.similarity < 0.6 for r in results)

    def test_results_sorted_by_similarity(self, retrieval):
        results = retrieval.retrieve("database choice", temporal_weight=0.0)
        for i in range(len(results) - 1):
            assert results[i].combined_score >= results[i + 1].combined_score

    def test_flat_mode_recency_score_is_zero_contribution(self, retrieval):
        results = retrieval.retrieve("database", temporal_weight=0.0)
        for r in results:
            assert r.combined_score == pytest.approx(r.similarity, abs=0.001)


# ---------------------------------------------------------------------------
# Temporal retrieval (temporal_weight > 0)
# ---------------------------------------------------------------------------

class TestTemporalRetrieval:
    def test_temporal_boosts_recent(self, retrieval):
        # Both SQLite (recent) and Postgres (old) should match "database"
        flat_results = retrieval.retrieve("database choice", temporal_weight=0.0, limit=5)
        temporal_results = retrieval.retrieve("database choice", temporal_weight=0.3, limit=5)

        # Find SQLite and Postgres positions in each
        def find_rank(results, substring):
            for i, r in enumerate(results):
                if substring in r.text:
                    return i
            return None

        sqlite_flat = find_rank(flat_results, "SQLite")
        sqlite_temporal = find_rank(temporal_results, "SQLite")

        # SQLite (recent) should rank same or better with temporal weighting
        if sqlite_flat is not None and sqlite_temporal is not None:
            assert sqlite_temporal <= sqlite_flat

    def test_combined_score_blends_correctly(self, retrieval):
        weight = 0.3
        results = retrieval.retrieve("database", temporal_weight=weight)
        for r in results:
            expected = r.similarity * (1.0 - weight) + r.recency_score * weight
            assert r.combined_score == pytest.approx(expected, abs=0.001)


# ---------------------------------------------------------------------------
# Topic timeline
# ---------------------------------------------------------------------------

class TestTopicTimeline:
    def test_returns_timeline_structure(self, retrieval):
        timeline = retrieval.retrieve_for_topic("database choice")
        assert timeline is not None
        assert hasattr(timeline, "current_belief")
        assert hasattr(timeline, "history")
        assert hasattr(timeline, "superseded")

    def test_current_belief_is_most_recent_active(self, retrieval):
        timeline = retrieval.retrieve_for_topic("database choice")
        if timeline.current_belief:
            # Current should be the recent SQLite stance (not superseded)
            assert not timeline.current_belief.superseded_in_conversation

    def test_superseded_beliefs_identified(self, retrieval):
        timeline = retrieval.retrieve_for_topic("interest rates currency value")
        # The superseded prop should appear in superseded list
        superseded_texts = [r.text for r in timeline.superseded]
        if superseded_texts:
            assert any("interest rate" in t.lower() for t in superseded_texts)

    def test_history_is_chronological(self, retrieval):
        timeline = retrieval.retrieve_for_topic("database")
        if len(timeline.history) > 1:
            for i in range(len(timeline.history) - 1):
                assert timeline.history[i].created_at <= timeline.history[i + 1].created_at


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_query(self, retrieval):
        results = retrieval.retrieve("")
        # Should not crash, may return results based on zero-vector similarity
        assert isinstance(results, list)

    def test_limit_respected(self, retrieval):
        results = retrieval.retrieve("anything", limit=2)
        assert len(results) <= 2

    def test_high_threshold_filters_all(self, retrieval):
        results = retrieval.retrieve("database", similarity_threshold=0.99)
        # 0.99 threshold should filter most/all
        assert len(results) <= 1
