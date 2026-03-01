"""
Tests for Phase 5 pattern-opinion generation (Task 5.8).

Detects recurring annotation patterns: frequency of same type+key,
scoped to timeframe, with provisional language.
"""

import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace, Annotation
from services.patterns import PatternService


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_patterns.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    s = SQLiteTraceStorage(db_path)
    yield s
    s.close()


def add_trace_with_annotation(
    storage, content, ann_type, ann_key, ann_value,
    days_ago=0, conversation_id="conv-001",
):
    now = datetime.now(timezone.utc)
    t = Trace(
        id=str(uuid.uuid4()),
        timestamp=(now - timedelta(days=days_ago)).isoformat(),
        content=content,
        conversation_id=conversation_id,
        source="user",
    )
    storage.store_trace(t)
    ann = Annotation(
        id=str(uuid.uuid4()),
        trace_id=t.id,
        type=ann_type,
        key=ann_key,
        value=ann_value,
        confidence=0.9,
        extracted_at=now.isoformat(),
        extractor="test",
    )
    storage.store_annotation(ann)
    return t


class TestFrequencyPatterns:
    def test_detects_frequent_annotation(self, storage):
        """3+ annotations with same type+key within 2 weeks triggers pattern."""
        for i in range(4):
            add_trace_with_annotation(
                storage, f"Training decision {i}",
                "decision", "training_program", f"change {i}",
                days_ago=i * 3,
            )

        service = PatternService(storage)
        patterns = service.detect_patterns(days=14)

        assert len(patterns) >= 1
        training_patterns = [p for p in patterns if "training" in p.description.lower()]
        assert len(training_patterns) >= 1

    def test_includes_trace_ids(self, storage):
        """Pattern includes all contributing trace IDs."""
        traces = []
        for i in range(3):
            t = add_trace_with_annotation(
                storage, f"Rowing session {i}",
                "measurable", "rowing_time", f"8:{i:02d}",
                days_ago=i * 2,
            )
            traces.append(t)

        service = PatternService(storage)
        patterns = service.detect_patterns(days=14)

        assert len(patterns) >= 1
        pattern = patterns[0]
        for t in traces:
            assert t.id in pattern.trace_ids

    def test_provisional_language(self, storage):
        """Pattern descriptions use provisional language (tilde, ~)."""
        for i in range(4):
            add_trace_with_annotation(
                storage, f"Career thought {i}",
                "decision", "career", f"option {i}",
                days_ago=i,
            )

        service = PatternService(storage)
        patterns = service.detect_patterns(days=14)

        assert len(patterns) >= 1
        desc = patterns[0].description
        assert "~" in desc or "about" in desc.lower()

    def test_no_annotations_returns_empty(self, storage):
        """Zero annotations means zero patterns."""
        service = PatternService(storage)
        patterns = service.detect_patterns(days=14)
        assert patterns == []

    def test_scoped_to_timeframe(self, storage):
        """Old annotations outside the timeframe are excluded."""
        # 3 recent
        for i in range(3):
            add_trace_with_annotation(
                storage, f"Recent {i}",
                "decision", "focus", f"val {i}",
                days_ago=i,
            )
        # 3 old (outside 14-day window)
        for i in range(3):
            add_trace_with_annotation(
                storage, f"Old {i}",
                "decision", "focus", f"old_val {i}",
                days_ago=30 + i,
            )

        service = PatternService(storage)
        patterns = service.detect_patterns(days=14)

        if patterns:
            # Should only reference recent traces
            for p in patterns:
                assert len(p.trace_ids) == 3, \
                    f"Expected 3 recent traces, got {len(p.trace_ids)}"

    def test_below_threshold_no_pattern(self, storage):
        """Fewer than 3 occurrences doesn't trigger a pattern."""
        for i in range(2):
            add_trace_with_annotation(
                storage, f"Trace {i}",
                "decision", "stack", f"option {i}",
                days_ago=i,
            )

        service = PatternService(storage)
        patterns = service.detect_patterns(days=14)

        stack_patterns = [p for p in patterns if "stack" in (p.description or "").lower()]
        assert len(stack_patterns) == 0
