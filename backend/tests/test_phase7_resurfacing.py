"""
Tests for Phase 7 "On This Day" resurfacing (Task 7.5).

When a new conversation starts, the system checks for meaningful traces
at temporal landmarks (~1 week, ~1 month, ~1 quarter ago). Candidates
are filtered to user traces with annotations, scored by richness.

Design: TASKS_PHASE7.md § Task 7.5
"""

import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace, Annotation
from services.embedding.bge import BGEBaseEmbedding
from services.resurfacing import ResurfacingService, ResurfaceCandidate


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_embedder():
    return BGEBaseEmbedding()


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_resurfacing.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    s = SQLiteTraceStorage(db_path)
    yield s
    s.close()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def store_trace_at(
    storage: SQLiteTraceStorage,
    content: str,
    timestamp: datetime,
    source: str = "user",
    conversation_id: str = "conv-001",
) -> Trace:
    """Store a trace at a specific timestamp."""
    t = Trace(
        id=str(uuid.uuid4()),
        timestamp=timestamp.isoformat(),
        content=content,
        conversation_id=conversation_id,
        source=source,
    )
    storage.store_trace(t)
    return t


def add_annotations(
    storage: SQLiteTraceStorage,
    trace_id: str,
    count: int = 2,
) -> list[Annotation]:
    """Add N dummy annotations to a trace."""
    annotations = []
    for i in range(count):
        ann = Annotation(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            type="topic",
            key=f"topic_{i}",
            value=f"value_{i}",
            confidence=0.8,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extractor="test",
        )
        storage.store_annotation(ann)
        annotations.append(ann)
    return annotations


# ------------------------------------------------------------------
# find_resurface_candidates tests
# ------------------------------------------------------------------


class TestFindResurfaceCandidates:
    def test_finds_traces_from_one_week_ago(self, storage):
        """Traces from ~7 days ago are found within ±1 day tolerance."""
        now = datetime.now(timezone.utc)

        # Trace exactly 7 days ago
        t = store_trace_at(storage, "Thinking about career direction", now - timedelta(days=7))
        add_annotations(storage, t.id, count=3)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)

        assert len(candidates) == 1
        assert candidates[0].trace.id == t.id
        assert candidates[0].window_label == "~1 week ago"

    def test_finds_traces_from_one_month_ago(self, storage):
        """Traces from ~30 days ago are found within ±2 day tolerance."""
        now = datetime.now(timezone.utc)

        t = store_trace_at(storage, "Started learning PyTorch", now - timedelta(days=29))
        add_annotations(storage, t.id, count=2)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)

        assert len(candidates) == 1
        assert candidates[0].window_label == "~1 month ago"

    def test_finds_traces_from_one_quarter_ago(self, storage):
        """Traces from ~90 days ago are found within ±3 day tolerance."""
        now = datetime.now(timezone.utc)

        t = store_trace_at(storage, "First day of the semester", now - timedelta(days=91))
        add_annotations(storage, t.id, count=2)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)

        assert len(candidates) == 1
        assert candidates[0].window_label == "~3 months ago"

    def test_filters_to_user_traces_only(self, storage):
        """Assistant traces are not surfaced, even with annotations."""
        now = datetime.now(timezone.utc)

        # Assistant trace at 7 days ago
        t_asst = store_trace_at(
            storage, "Here are some suggestions", now - timedelta(days=7),
            source="assistant",
        )
        add_annotations(storage, t_asst.id, count=5)

        # User trace at 7 days ago
        t_user = store_trace_at(
            storage, "I want to explore AI careers", now - timedelta(days=7),
        )
        add_annotations(storage, t_user.id, count=2)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)

        assert len(candidates) == 1
        assert candidates[0].trace.source == "user"

    def test_filters_traces_without_annotations(self, storage):
        """Traces with zero annotations are skipped (empty chatter)."""
        now = datetime.now(timezone.utc)

        # User trace with no annotations
        store_trace_at(storage, "hi", now - timedelta(days=7))

        # User trace with annotations
        t = store_trace_at(storage, "Decided to drop rowing goal", now - timedelta(days=7, hours=1))
        add_annotations(storage, t.id, count=3)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)

        assert len(candidates) == 1
        assert candidates[0].trace.id == t.id

    def test_max_three_candidates(self, storage):
        """Never returns more than 3 candidates."""
        now = datetime.now(timezone.utc)

        # Traces at all three windows
        for days_ago in [7, 30, 90]:
            t = store_trace_at(
                storage, f"Trace from {days_ago} days ago",
                now - timedelta(days=days_ago),
            )
            add_annotations(storage, t.id, count=2)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)

        assert len(candidates) <= 3

    def test_empty_when_no_traces_at_landmarks(self, storage):
        """No traces at any temporal landmark → empty list."""
        now = datetime.now(timezone.utc)

        # Trace from 3 days ago — doesn't hit any window
        t = store_trace_at(storage, "Recent trace", now - timedelta(days=3))
        add_annotations(storage, t.id, count=5)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)

        assert candidates == []

    def test_empty_when_no_traces_at_all(self, storage):
        """Completely empty storage → empty list, no crash."""
        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates()

        assert candidates == []

    def test_picks_richest_trace_per_window(self, storage):
        """Multiple traces in same window → picks the one with most annotations."""
        now = datetime.now(timezone.utc)

        t_poor = store_trace_at(
            storage, "Brief thought about training",
            now - timedelta(days=7, hours=2),
        )
        add_annotations(storage, t_poor.id, count=1)

        t_rich = store_trace_at(
            storage, "Deep analysis of thoracic pump hypothesis",
            now - timedelta(days=7, hours=1),
        )
        add_annotations(storage, t_rich.id, count=5)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)

        assert len(candidates) == 1
        assert candidates[0].trace.id == t_rich.id
        assert candidates[0].annotation_count == 5

    def test_tolerance_boundaries(self, storage):
        """Trace at edge of tolerance window (7+1=8 days ago) is still found."""
        now = datetime.now(timezone.utc)

        # Exactly at tolerance boundary: 8 days ago (7+1)
        t = store_trace_at(storage, "Edge case trace", now - timedelta(days=8))
        add_annotations(storage, t.id, count=2)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)

        assert len(candidates) == 1

    def test_outside_tolerance_not_found(self, storage):
        """Trace outside tolerance window (9 days ago for 7±1) is not found."""
        now = datetime.now(timezone.utc)

        t = store_trace_at(storage, "Too far trace", now - timedelta(days=9))
        add_annotations(storage, t.id, count=5)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)

        assert candidates == []


# ------------------------------------------------------------------
# format_for_prompt tests
# ------------------------------------------------------------------


class TestFormatForPrompt:
    def test_formats_candidates_naturally(self, storage):
        """Candidates produce a readable prompt section."""
        now = datetime.now(timezone.utc)

        t = store_trace_at(storage, "Exploring vector databases for RAG", now - timedelta(days=7))
        add_annotations(storage, t.id, count=3)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)
        prompt_section = service.format_for_prompt(candidates)

        assert "Echoes from your past thinking" in prompt_section
        assert "~1 week ago" in prompt_section
        assert "vector databases" in prompt_section
        assert "If relevant" in prompt_section

    def test_empty_candidates_returns_empty_string(self, storage):
        """No candidates → empty string (no noise in prompt)."""
        service = ResurfacingService(storage)
        assert service.format_for_prompt([]) == ""

    def test_truncates_long_content(self, storage):
        """Long trace content is truncated for prompt budget."""
        now = datetime.now(timezone.utc)

        long_content = "A " * 200  # 400 chars
        t = store_trace_at(storage, long_content, now - timedelta(days=7))
        add_annotations(storage, t.id, count=2)

        service = ResurfacingService(storage)
        candidates = service.find_resurface_candidates(current_time=now)
        prompt_section = service.format_for_prompt(candidates)

        # Should be truncated (original is 400 chars)
        assert "…" in prompt_section or len(prompt_section) < len(long_content) + 100
