"""
Tests for Phase 5 contradiction detection (Task 5.4).

Detects pairs of retrieved traces that address the same topic but
express opposing positions. Flags them for the LLM to present as
evolution ("in January you leaned toward X, by March you shifted to Y").
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace, Annotation
from services.trace_retrieval import TraceRetrievalResult
from services.contradiction import ContradictionDetector


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_contradiction.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    s = SQLiteTraceStorage(db_path)
    yield s
    s.close()


def make_result(
    content, source="user", conversation_id="conv-001",
    timestamp=None, similarity=0.8, combined=0.7,
):
    t = Trace(
        id=str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        content=content,
        conversation_id=conversation_id,
        source=source,
    )
    return TraceRetrievalResult(trace=t, similarity=similarity, recency=1.0, combined=combined)


def store_annotation(storage, trace_id, ann_type, key, value, confidence=0.9):
    ann = Annotation(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        type=ann_type,
        key=key,
        value=value,
        confidence=confidence,
        extracted_at=datetime.now(timezone.utc).isoformat(),
        extractor="test",
    )
    storage.store_annotation(ann)
    return ann


class TestContradictionDetection:
    def test_opposing_decisions_flagged(self, storage):
        """Two traces with same decision key but different values are contradictory."""
        now = datetime.now(timezone.utc)
        r1 = make_result(
            "I decided to focus on rowing for my 2K goal",
            timestamp=(now - timedelta(weeks=4)).isoformat(),
        )
        r2 = make_result(
            "I'm dropping the 2K row goal entirely",
            timestamp=now.isoformat(),
        )
        storage.store_trace(r1.trace)
        storage.store_trace(r2.trace)
        store_annotation(storage, r1.trace.id, "decision", "rowing_goal", "focus on 2K")
        store_annotation(storage, r2.trace.id, "decision", "rowing_goal", "dropped")

        detector = ContradictionDetector(storage)
        contradictions = detector.detect([r1, r2])

        assert len(contradictions) == 1
        # Ordered chronologically: earlier first
        assert contradictions[0] == (r1.trace.id, r2.trace.id)

    def test_consistent_decisions_not_flagged(self, storage):
        """Two traces with same decision key and same value are NOT contradictory."""
        now = datetime.now(timezone.utc)
        r1 = make_result(
            "I want to pursue AI engineering",
            timestamp=(now - timedelta(weeks=2)).isoformat(),
        )
        r2 = make_result(
            "AI engineering is still my top career choice",
            timestamp=now.isoformat(),
        )
        storage.store_trace(r1.trace)
        storage.store_trace(r2.trace)
        store_annotation(storage, r1.trace.id, "decision", "career", "AI engineering")
        store_annotation(storage, r2.trace.id, "decision", "career", "AI engineering")

        detector = ContradictionDetector(storage)
        contradictions = detector.detect([r1, r2])

        assert len(contradictions) == 0

    def test_different_topics_not_flagged(self, storage):
        """Two traces about different topics are never contradictory."""
        now = datetime.now(timezone.utc)
        r1 = make_result("I chose Python for the backend", timestamp=now.isoformat())
        r2 = make_result("I dropped rowing", timestamp=now.isoformat())
        storage.store_trace(r1.trace)
        storage.store_trace(r2.trace)
        store_annotation(storage, r1.trace.id, "decision", "backend_lang", "Python")
        store_annotation(storage, r2.trace.id, "decision", "rowing_goal", "dropped")

        detector = ContradictionDetector(storage)
        contradictions = detector.detect([r1, r2])

        assert len(contradictions) == 0

    def test_no_annotations_returns_empty(self, storage):
        """Traces without annotations can't contradict."""
        r1 = make_result("Some message")
        r2 = make_result("Another message")
        storage.store_trace(r1.trace)
        storage.store_trace(r2.trace)

        detector = ContradictionDetector(storage)
        contradictions = detector.detect([r1, r2])

        assert contradictions == []

    def test_contradictions_ordered_chronologically(self, storage):
        """Earlier trace is always first in the pair."""
        now = datetime.now(timezone.utc)
        # r_new is created first in the list but has a later timestamp
        r_new = make_result(
            "Dropping rowing",
            timestamp=now.isoformat(),
        )
        r_old = make_result(
            "Focusing on rowing",
            timestamp=(now - timedelta(weeks=4)).isoformat(),
        )
        storage.store_trace(r_new.trace)
        storage.store_trace(r_old.trace)
        store_annotation(storage, r_new.trace.id, "decision", "rowing", "dropped")
        store_annotation(storage, r_old.trace.id, "decision", "rowing", "focus")

        detector = ContradictionDetector(storage)
        # Pass in reverse chronological order
        contradictions = detector.detect([r_new, r_old])

        assert len(contradictions) == 1
        assert contradictions[0][0] == r_old.trace.id  # older first
        assert contradictions[0][1] == r_new.trace.id

    def test_empty_results_returns_empty(self, storage):
        """Empty retrieval results produce no contradictions."""
        detector = ContradictionDetector(storage)
        assert detector.detect([]) == []

    def test_single_result_returns_empty(self, storage):
        """Can't contradict with only one trace."""
        r = make_result("Only one trace")
        storage.store_trace(r.trace)
        store_annotation(storage, r.trace.id, "decision", "career", "AI")

        detector = ContradictionDetector(storage)
        assert detector.detect([r]) == []


class TestContradictionInSystemPrompt:
    """Task 5.4 acceptance criterion 6: system prompt includes evolution cue."""

    def test_prompt_includes_evolution_cue(self, storage):
        """When contradictions detected, system prompt mentions evolution."""
        from unittest.mock import MagicMock
        from services.trace_context import TraceContextAssembly
        from services.trace_retrieval import TraceRetrievalService, TraceRetrievalResult

        now = datetime.now(timezone.utc)
        r1 = make_result(
            "I want to focus on rowing for my 2K goal",
            timestamp=(now - timedelta(weeks=4)).isoformat(),
        )
        r2 = make_result(
            "I'm dropping the rowing goal entirely",
            timestamp=now.isoformat(),
        )
        storage.store_trace(r1.trace)
        storage.store_trace(r2.trace)
        store_annotation(storage, r1.trace.id, "decision", "rowing", "focus on 2K")
        store_annotation(storage, r2.trace.id, "decision", "rowing", "dropped")

        # Mock retrieval to return our controlled results
        mock_retrieval = MagicMock(spec=TraceRetrievalService)
        mock_retrieval.retrieve.return_value = [r1, r2]

        detector = ContradictionDetector(storage)
        assembly = TraceContextAssembly(mock_retrieval, contradiction_detector=detector)

        prompt, ids = assembly.build_system_prompt("rowing goals")

        assert prompt is not None
        assert "evolution" in prompt.lower()
        assert "[1] and [2]" in prompt
