"""
Tests for Phase 5 annotation wiring (Tasks 5.1 + 5.3).

Tests that the background processing function:
  - Extracts annotations for user and assistant traces
  - Stores annotations in the database
  - Creates temporal connections between traces
  - Handles extraction failures gracefully

Tests the function directly (not through HTTP) — the HTTP wiring
is a thin call to this function from chat.py's generate().
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace, Connection
from services.annotation import AnnotationExtractionService
from services.connections import ConnectionService


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


# ------------------------------------------------------------------
# Mock provider
# ------------------------------------------------------------------


class MockAnnotationProvider:
    """Returns configurable annotation responses per call."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self._call_count = 0
        self.calls = []

    async def complete(self, prompt, *, system_prompt=None, model=None, max_tokens=None):
        self.calls.append(prompt)
        if self._call_count < len(self.responses):
            resp = self.responses[self._call_count]
        else:
            resp = "[]"
        self._call_count += 1
        return resp

    async def vision(self, image_base64, prompt):
        return ""


class FailingProvider:
    """Always raises on complete()."""

    async def complete(self, prompt, *, system_prompt=None, model=None, max_tokens=None):
        raise Exception("LLM is down")

    async def vision(self, image_base64, prompt):
        return ""


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_wiring.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    s = SQLiteTraceStorage(db_path)
    yield s
    s.close()


def make_trace(
    content="test",
    source="user",
    conversation_id="conv-001",
    parent_trace_id=None,
    timestamp=None,
):
    return Trace(
        id=str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        content=content,
        conversation_id=conversation_id,
        parent_trace_id=parent_trace_id,
        source=source,
    )


def store_trace_chain(storage, messages, conversation_id="conv-001"):
    """Store a chain of traces with parent links. Returns list of Trace objects."""
    traces = []
    parent_id = None
    for i, (source, content) in enumerate(messages):
        t = make_trace(
            content=content,
            source=source,
            conversation_id=conversation_id,
            parent_trace_id=parent_id,
            timestamp=(datetime.now(timezone.utc) + timedelta(seconds=i)).isoformat(),
        )
        storage.store_trace(t)
        parent_id = t.id
        traces.append(t)
    return traces


# ------------------------------------------------------------------
# Import the background function — this is what we're testing
# ------------------------------------------------------------------

from services.background import process_traces_background


# ------------------------------------------------------------------
# Task 5.1: Annotation extraction in background
# ------------------------------------------------------------------


class TestAnnotationWiring:
    @pytest.mark.asyncio
    async def test_user_trace_gets_annotations(self, storage):
        """After background processing, user trace has annotations in DB."""
        user_annotations = json.dumps([
            {"type": "decision", "key": "career", "value": "chose AI", "confidence": 0.9},
        ])
        provider = MockAnnotationProvider(responses=[user_annotations, "[]"])
        annotation_svc = AnnotationExtractionService(provider)
        connection_svc = ConnectionService(storage)

        traces = store_trace_chain(storage, [
            ("user", "I've decided to pursue AI engineering"),
            ("assistant", "That's a great choice given your background."),
        ])

        await process_traces_background(
            user_trace=traces[0],
            assistant_trace=traces[1],
            conversation_id="conv-001",
            storage=storage,
            annotation_service=annotation_svc,
            connection_service=connection_svc,
        )

        annotations = storage.get_annotations_for_trace(traces[0].id)
        assert len(annotations) == 1
        assert annotations[0].type == "decision"
        assert annotations[0].key == "career"

    @pytest.mark.asyncio
    async def test_assistant_trace_gets_annotations(self, storage):
        """After background processing, assistant trace has annotations in DB."""
        asst_annotations = json.dumps([
            {"type": "topic", "key": "AI engineering", "value": "career recommendation"},
        ])
        provider = MockAnnotationProvider(responses=["[]", asst_annotations])
        annotation_svc = AnnotationExtractionService(provider)
        connection_svc = ConnectionService(storage)

        traces = store_trace_chain(storage, [
            ("user", "What should I focus on?"),
            ("assistant", "AI engineering is a strong path for your skills."),
        ])

        await process_traces_background(
            user_trace=traces[0],
            assistant_trace=traces[1],
            conversation_id="conv-001",
            storage=storage,
            annotation_service=annotation_svc,
            connection_service=connection_svc,
        )

        annotations = storage.get_annotations_for_trace(traces[1].id)
        assert len(annotations) == 1
        assert annotations[0].type == "topic"

    @pytest.mark.asyncio
    async def test_extraction_failure_does_not_crash(self, storage):
        """If LLM fails, traces and connections still exist, no exception raised."""
        annotation_svc = AnnotationExtractionService(FailingProvider())
        connection_svc = ConnectionService(storage)

        traces = store_trace_chain(storage, [
            ("user", "Test message"),
            ("assistant", "Test response"),
        ])

        # Should not raise
        await process_traces_background(
            user_trace=traces[0],
            assistant_trace=traces[1],
            conversation_id="conv-001",
            storage=storage,
            annotation_service=annotation_svc,
            connection_service=connection_svc,
        )

        # Traces still exist
        assert storage.get_trace(traces[0].id) is not None
        assert storage.get_trace(traces[1].id) is not None

        # No annotations (extraction failed), but no crash
        assert storage.get_annotations_for_trace(traces[0].id) == []

    @pytest.mark.asyncio
    async def test_multiple_annotations_per_trace(self, storage):
        """Multiple annotations from a single trace are all stored."""
        multi = json.dumps([
            {"type": "decision", "key": "stack", "value": "chose FastAPI", "confidence": 0.9},
            {"type": "emotion", "key": "excitement", "value": "about the project", "confidence": 0.7},
            {"type": "commitment", "key": "demo", "value": "ship by March 31", "confidence": 0.8},
        ])
        provider = MockAnnotationProvider(responses=[multi, "[]"])
        annotation_svc = AnnotationExtractionService(provider)
        connection_svc = ConnectionService(storage)

        traces = store_trace_chain(storage, [
            ("user", "I chose FastAPI, excited about the project, demo by March 31"),
            ("assistant", "Sounds good."),
        ])

        await process_traces_background(
            user_trace=traces[0],
            assistant_trace=traces[1],
            conversation_id="conv-001",
            storage=storage,
            annotation_service=annotation_svc,
            connection_service=connection_svc,
        )

        annotations = storage.get_annotations_for_trace(traces[0].id)
        assert len(annotations) == 3
        types = {a.type for a in annotations}
        assert types == {"decision", "emotion", "commitment"}


# ------------------------------------------------------------------
# Task 5.3: Temporal connections in background
# ------------------------------------------------------------------


class TestTemporalConnectionWiring:
    @pytest.mark.asyncio
    async def test_user_to_assistant_temporal_connection(self, storage):
        """Background creates temporal connection: user_trace → assistant_trace."""
        provider = MockAnnotationProvider(responses=["[]", "[]"])
        annotation_svc = AnnotationExtractionService(provider)
        connection_svc = ConnectionService(storage)

        traces = store_trace_chain(storage, [
            ("user", "Hello"),
            ("assistant", "Hi there"),
        ])

        await process_traces_background(
            user_trace=traces[0],
            assistant_trace=traces[1],
            conversation_id="conv-001",
            storage=storage,
            annotation_service=annotation_svc,
            connection_service=connection_svc,
        )

        connections = storage.get_connections_for_trace(traces[0].id)
        temporal = [c for c in connections if c.type == "temporal"]
        assert len(temporal) >= 1
        # user → assistant connection exists
        assert any(
            c.source_id == traces[0].id and c.target_id == traces[1].id
            for c in temporal
        )

    @pytest.mark.asyncio
    async def test_parent_to_user_temporal_connection(self, storage):
        """If user trace has a parent, temporal connection: parent → user exists."""
        provider = MockAnnotationProvider(responses=["[]", "[]"])
        annotation_svc = AnnotationExtractionService(provider)
        connection_svc = ConnectionService(storage)

        # First round: two traces
        first_traces = store_trace_chain(storage, [
            ("user", "First message"),
            ("assistant", "First response"),
        ])

        # Second round: user trace has parent = first assistant trace
        user2 = make_trace(
            content="Follow-up question",
            source="user",
            conversation_id="conv-001",
            parent_trace_id=first_traces[1].id,
        )
        storage.store_trace(user2)
        asst2 = make_trace(
            content="Follow-up answer",
            source="assistant",
            conversation_id="conv-001",
            parent_trace_id=user2.id,
        )
        storage.store_trace(asst2)

        await process_traces_background(
            user_trace=user2,
            assistant_trace=asst2,
            conversation_id="conv-001",
            storage=storage,
            annotation_service=annotation_svc,
            connection_service=connection_svc,
        )

        # parent (first_traces[1]) → user2 connection
        connections = storage.get_connections_for_trace(user2.id)
        temporal = [c for c in connections if c.type == "temporal"]
        parent_to_user = [
            c for c in temporal
            if c.source_id == first_traces[1].id and c.target_id == user2.id
        ]
        assert len(parent_to_user) == 1

        # user2 → asst2 connection
        user_to_asst = [
            c for c in temporal
            if c.source_id == user2.id and c.target_id == asst2.id
        ]
        assert len(user_to_asst) == 1

    @pytest.mark.asyncio
    async def test_no_semantic_connections_per_message(self, storage):
        """Background task does NOT compute semantic connections (batch only)."""
        provider = MockAnnotationProvider(responses=["[]", "[]"])
        annotation_svc = AnnotationExtractionService(provider)
        connection_svc = ConnectionService(storage)

        traces = store_trace_chain(storage, [
            ("user", "Test"),
            ("assistant", "Response"),
        ])

        await process_traces_background(
            user_trace=traces[0],
            assistant_trace=traces[1],
            conversation_id="conv-001",
            storage=storage,
            annotation_service=annotation_svc,
            connection_service=connection_svc,
        )

        semantic = storage.get_connections_by_type("semantic")
        assert len(semantic) == 0
