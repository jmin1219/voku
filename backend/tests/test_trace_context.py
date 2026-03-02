"""
Tests for v2 trace context assembly.

Tests the formatting layer: given retrieval results, does the system
prompt contain the right structure, trace references, and time labels?

Uses a mock retrieval service to control what traces are returned,
plus an integration test that goes storage → embed → retrieve → assemble.
"""

import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace
from services.trace_retrieval import TraceRetrievalService, TraceRetrievalResult
from services.trace_context import (
    TraceContextAssembly,
    _source_label,
    _relative_time,
    _truncate,
    MAX_TRACE_CHARS,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


def make_retrieval_result(
    content: str = "test content",
    source: str = "user",
    timestamp: str | None = None,
    similarity: float = 0.8,
    recency: float = 0.9,
    combined: float = 0.85,
) -> TraceRetrievalResult:
    """Create a TraceRetrievalResult with controlled values."""
    return TraceRetrievalResult(
        trace=Trace(
            id=str(uuid.uuid4()),
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            content=content,
            source=source,
            conversation_id="conv-001",
        ),
        similarity=similarity,
        recency=recency,
        combined=combined,
    )


# ------------------------------------------------------------------
# Helper function unit tests
# ------------------------------------------------------------------


class TestSourceLabel:
    def test_user(self):
        assert _source_label("user") == "you"

    def test_assistant(self):
        assert _source_label("assistant") == "assistant"

    def test_resource(self):
        assert _source_label("resource") == "resource"

    def test_system(self):
        assert _source_label("system") == "system"

    def test_unknown_passes_through(self):
        assert _source_label("custom") == "custom"


class TestRelativeTime:
    def test_just_now(self):
        now = datetime.now(timezone.utc)
        assert _relative_time(now.isoformat(), now) == "just now"

    def test_minutes(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(minutes=5)).isoformat()
        assert _relative_time(ts, now) == "5 minutes ago"

    def test_one_minute(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(minutes=1, seconds=10)).isoformat()
        assert _relative_time(ts, now) == "1 minute ago"

    def test_hours(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(hours=3)).isoformat()
        assert _relative_time(ts, now) == "3 hours ago"

    def test_days(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=2)).isoformat()
        assert _relative_time(ts, now) == "2 days ago"

    def test_weeks(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(weeks=2)).isoformat()
        assert _relative_time(ts, now) == "2 weeks ago"

    def test_months(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=60)).isoformat()
        assert _relative_time(ts, now) == "2 months ago"

    def test_unparseable(self):
        now = datetime.now(timezone.utc)
        assert _relative_time("bad-date", now) == "unknown time"


class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("Hello world.", 500) == "Hello world."

    def test_long_text_cut_at_sentence(self):
        text = "First sentence. Second sentence. Third sentence that is long."
        result = _truncate(text, 35)
        assert result.endswith(".")
        assert len(result) <= 35

    def test_long_text_fallback_to_space(self):
        text = "One very long sentence without any period breaks for a while here"
        result = _truncate(text, 40)
        assert result.endswith("…")
        assert len(result) <= 41  # +1 for the ellipsis char

    def test_exact_length_unchanged(self):
        text = "x" * 500
        assert _truncate(text, 500) == text


# ------------------------------------------------------------------
# Context assembly
# ------------------------------------------------------------------


class TestBuildSystemPrompt:
    def test_returns_prompt_and_ids(self):
        """Basic call returns a string prompt and trace ID list."""
        mock_retrieval = MagicMock()
        results = [make_retrieval_result(content="Past context")]
        mock_retrieval.retrieve.return_value = results

        assembly = TraceContextAssembly(mock_retrieval)
        prompt, ids = assembly.build_system_prompt("current question")

        assert prompt is not None
        assert len(ids) == 1
        assert ids[0] == results[0].trace.id

    def test_returns_base_prompt_when_no_traces(self):
        """Empty retrieval returns base prompt (with date) and empty IDs."""
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = []

        assembly = TraceContextAssembly(mock_retrieval)
        prompt, ids = assembly.build_system_prompt("any query")

        assert prompt is not None
        assert "Voku" in prompt
        assert "Today is" in prompt
        assert ids == []

    def test_prompt_contains_identity_preamble(self):
        """Prompt starts with Voku identity."""
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = [make_retrieval_result()]

        assembly = TraceContextAssembly(mock_retrieval)
        prompt, _ = assembly.build_system_prompt("query")

        assert "Voku" in prompt
        assert "thinking environment" in prompt
        assert "Today is" in prompt

    def test_prompt_contains_numbered_traces(self):
        """Retrieved traces appear with [1], [2] index markers."""
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = [
            make_retrieval_result(content="First trace"),
            make_retrieval_result(content="Second trace"),
        ]

        assembly = TraceContextAssembly(mock_retrieval)
        prompt, _ = assembly.build_system_prompt("query")

        assert "[1]" in prompt
        assert "[2]" in prompt
        assert "First trace" in prompt
        assert "Second trace" in prompt

    def test_prompt_contains_source_labels(self):
        """User traces labeled 'you', assistant traces labeled 'assistant'."""
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = [
            make_retrieval_result(content="User said this", source="user"),
            make_retrieval_result(content="AI responded", source="assistant"),
        ]

        assembly = TraceContextAssembly(mock_retrieval)
        prompt, _ = assembly.build_system_prompt("query")

        assert "(you," in prompt
        assert "(assistant," in prompt

    def test_prompt_contains_relative_timestamps(self):
        """Traces show relative time labels."""
        now = datetime.now(timezone.utc)
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = [
            make_retrieval_result(
                content="Recent message",
                timestamp=(now - timedelta(hours=2)).isoformat(),
            ),
        ]

        assembly = TraceContextAssembly(mock_retrieval)
        prompt, _ = assembly.build_system_prompt("query")

        assert "2 hours ago" in prompt

    def test_ids_ordered_by_combined_score(self):
        """Trace IDs returned in same order as retrieval (by combined score)."""
        r1 = make_retrieval_result(content="Top", combined=0.95)
        r2 = make_retrieval_result(content="Second", combined=0.80)
        r3 = make_retrieval_result(content="Third", combined=0.70)

        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = [r1, r2, r3]

        assembly = TraceContextAssembly(mock_retrieval)
        _, ids = assembly.build_system_prompt("query")

        assert ids == [r1.trace.id, r2.trace.id, r3.trace.id]

    def test_long_traces_truncated(self):
        """Traces exceeding MAX_TRACE_CHARS are truncated."""
        long_content = "Word " * 200  # ~1000 chars
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = [
            make_retrieval_result(content=long_content),
        ]

        assembly = TraceContextAssembly(mock_retrieval)
        prompt, _ = assembly.build_system_prompt("query")

        # The formatted trace line should be shorter than the original
        # (index + source + time + truncated content)
        assert long_content not in prompt

    def test_prompt_contains_usage_instructions(self):
        """Prompt ends with natural usage guidance."""
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = [make_retrieval_result()]

        assembly = TraceContextAssembly(mock_retrieval)
        prompt, _ = assembly.build_system_prompt("query")

        assert "naturally" in prompt.lower()


# ------------------------------------------------------------------
# Integration test — full pipeline
# ------------------------------------------------------------------


class TestIntegration:
    """End-to-end: store traces → embed → retrieve → assemble context."""

    def test_full_pipeline(self, tmp_path):
        """Vertical slice: traces with embeddings produce a usable system prompt."""
        # Setup storage
        db_path = tmp_path / "integration.db"
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_PATH.read_text())
        conn.close()

        storage = SQLiteTraceStorage(db_path)

        # Create a fake embedder
        class FakeEmbedder:
            model_name = "fake"
            def embed(self, text):
                return np.ones(768, dtype=np.float32)

        embedder = FakeEmbedder()

        # Store traces with embeddings
        now = datetime.now(timezone.utc)
        base_vec = np.ones(768, dtype=np.float32)

        for i in range(3):
            t = Trace(
                id=str(uuid.uuid4()),
                timestamp=(now - timedelta(days=i)).isoformat(),
                content=f"Conversation message {i} about rowing",
                conversation_id="conv-integration",
                source="user" if i % 2 == 0 else "assistant",
            )
            storage.store_trace(t)
            emb = base_vec + np.random.randn(768).astype(np.float32) * 0.05
            storage.store_embedding(t.id, emb, "fake")

        # Build retrieval + context assembly
        retrieval = TraceRetrievalService(storage, embedder)
        assembly = TraceContextAssembly(retrieval)

        # Assemble
        prompt, ids = assembly.build_system_prompt("Tell me about rowing")

        # Verify
        assert prompt is not None
        assert len(ids) == 3
        assert "Voku" in prompt
        assert "[1]" in prompt
        assert "[2]" in prompt
        assert "[3]" in prompt
        assert "rowing" in prompt

        storage.close()
