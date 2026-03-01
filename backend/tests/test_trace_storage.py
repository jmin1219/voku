"""
Tests for v2 trace storage layer.

Mirrors test_storage.py patterns from v1 but tests the trace-based
SQLiteTraceStorage. Uses pytest tmp_path for isolated databases.
"""

import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Annotation, Connection, Trace, SimilarTrace


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


# Path to the single source of truth for v2 schema
SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


@pytest.fixture
def storage(tmp_path):
    """Create a fresh SQLiteTraceStorage with v2 schema."""
    db_path = tmp_path / "test.db"
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()

    db = SQLiteTraceStorage(db_path)
    yield db
    db.close()


def make_trace(
    content: str = "test trace",
    source: str = "user",
    conversation_id: str | None = "conv-001",
    parent_trace_id: str | None = None,
    timestamp: str | None = None,
) -> Trace:
    """Helper to create a Trace with sensible defaults."""
    return Trace(
        id=str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        content=content,
        conversation_id=conversation_id,
        parent_trace_id=parent_trace_id,
        source=source,
    )


def random_embedding(dims: int = 768) -> np.ndarray:
    """Generate a random unit-norm embedding vector."""
    vec = np.random.randn(dims).astype(np.float32)
    return vec / (np.linalg.norm(vec) + 1e-10)


# ------------------------------------------------------------------
# Trace CRUD
# ------------------------------------------------------------------


class TestStoreTrace:
    def test_store_and_retrieve(self, storage):
        """Store a trace, retrieve it by ID, verify all fields."""
        trace = make_trace(content="I think rowing is hurting my ankle")
        storage.store_trace(trace)

        retrieved = storage.get_trace(trace.id)
        assert retrieved is not None
        assert retrieved.id == trace.id
        assert retrieved.content == trace.content
        assert retrieved.timestamp == trace.timestamp
        assert retrieved.conversation_id == trace.conversation_id
        assert retrieved.source == trace.source

    def test_store_returns_id(self, storage):
        trace = make_trace()
        returned_id = storage.store_trace(trace)
        assert returned_id == trace.id

    def test_get_nonexistent_returns_none(self, storage):
        assert storage.get_trace("nonexistent-id") is None

    def test_store_trace_with_parent(self, storage):
        """Parent trace linking — forms the conversation thread."""
        parent = make_trace(content="First message")
        storage.store_trace(parent)

        child = make_trace(
            content="Response to first",
            source="assistant",
            parent_trace_id=parent.id,
        )
        storage.store_trace(child)

        retrieved = storage.get_trace(child.id)
        assert retrieved.parent_trace_id == parent.id

    def test_store_trace_without_conversation(self, storage):
        """System traces can exist outside conversations."""
        trace = make_trace(
            content="System-generated resource",
            source="system",
            conversation_id=None,
        )
        storage.store_trace(trace)

        retrieved = storage.get_trace(trace.id)
        assert retrieved.conversation_id is None
        assert retrieved.source == "system"

    def test_store_all_source_types(self, storage):
        """All four source types defined in SPEC store correctly."""
        for source in ("user", "assistant", "resource", "system"):
            trace = make_trace(content=f"{source} trace", source=source)
            storage.store_trace(trace)
            retrieved = storage.get_trace(trace.id)
            assert retrieved.source == source

    def test_duplicate_id_raises(self, storage):
        """Trace IDs must be unique — immutability guarantee."""
        trace = make_trace()
        storage.store_trace(trace)
        with pytest.raises(Exception):  # sqlite3.IntegrityError
            storage.store_trace(trace)

    def test_content_preserved_exactly(self, storage):
        """Content is never modified — Constraint 2.11."""
        content = "  Whitespace matters.\n\nSo do newlines.  "
        trace = make_trace(content=content)
        storage.store_trace(trace)
        assert storage.get_trace(trace.id).content == content


# ------------------------------------------------------------------
# Conversation queries
# ------------------------------------------------------------------


class TestConversationQueries:
    def test_get_traces_by_conversation(self, storage):
        """Returns all traces in a conversation, timestamp-ordered."""
        base_time = datetime(2026, 2, 28, 12, 0, 0, tzinfo=timezone.utc)
        traces = []
        for i in range(3):
            t = make_trace(
                content=f"Message {i}",
                conversation_id="conv-A",
                timestamp=(base_time + timedelta(minutes=i)).isoformat(),
            )
            traces.append(t)
            storage.store_trace(t)

        result = storage.get_traces_by_conversation("conv-A")
        assert len(result) == 3
        assert result[0].content == "Message 0"
        assert result[2].content == "Message 2"

    def test_get_traces_filters_by_conversation(self, storage):
        """Only returns traces from the requested conversation."""
        storage.store_trace(make_trace(content="In A", conversation_id="conv-A"))
        storage.store_trace(make_trace(content="In B", conversation_id="conv-B"))

        result = storage.get_traces_by_conversation("conv-A")
        assert len(result) == 1
        assert result[0].content == "In A"

    def test_get_traces_empty_conversation(self, storage):
        assert storage.get_traces_by_conversation("nonexistent") == []

    def test_list_conversations(self, storage):
        """Lists conversations derived from trace groupings."""
        base_time = datetime(2026, 2, 28, 12, 0, 0, tzinfo=timezone.utc)

        # Conv A: 3 traces
        for i in range(3):
            storage.store_trace(make_trace(
                conversation_id="conv-A",
                timestamp=(base_time + timedelta(minutes=i)).isoformat(),
            ))

        # Conv B: 1 trace, more recent
        storage.store_trace(make_trace(
            conversation_id="conv-B",
            timestamp=(base_time + timedelta(hours=1)).isoformat(),
        ))

        convs = storage.list_conversations()
        assert len(convs) == 2

        # Most recent first
        assert convs[0]["id"] == "conv-B"
        assert convs[0]["trace_count"] == 1
        assert convs[1]["id"] == "conv-A"
        assert convs[1]["trace_count"] == 3

    def test_list_conversations_excludes_orphans(self, storage):
        """Traces with no conversation_id don't appear in listing."""
        storage.store_trace(make_trace(conversation_id="conv-A"))
        storage.store_trace(make_trace(conversation_id=None, source="system"))

        convs = storage.list_conversations()
        assert len(convs) == 1
        assert convs[0]["id"] == "conv-A"

    def test_list_conversations_empty_db(self, storage):
        assert storage.list_conversations() == []


# ------------------------------------------------------------------
# Embeddings + vector search
# ------------------------------------------------------------------


class TestEmbeddings:
    def test_store_and_find_similar(self, storage):
        """Store traces with embeddings, find similar by vector search."""
        t1 = make_trace(content="I love rowing")
        t2 = make_trace(content="Rowing is my favorite")
        storage.store_trace(t1)
        storage.store_trace(t2)

        # Create similar embeddings
        base = random_embedding()
        e1 = base + np.random.randn(768).astype(np.float32) * 0.05
        e2 = base + np.random.randn(768).astype(np.float32) * 0.05

        storage.store_embedding(t1.id, e1, "bge-base-en-v1.5")
        storage.store_embedding(t2.id, e2, "bge-base-en-v1.5")

        # Query with base vector — both should match
        results = storage.find_similar(base, threshold=0.5, limit=10)
        assert len(results) == 2
        assert all(isinstance(r, SimilarTrace) for r in results)
        # Sorted by score descending
        assert results[0].score >= results[1].score

    def test_find_similar_threshold_filtering(self, storage):
        """Traces below threshold are excluded."""
        t1 = make_trace(content="Close match")
        t2 = make_trace(content="Distant topic")
        storage.store_trace(t1)
        storage.store_trace(t2)

        close_vec = np.ones(768, dtype=np.float32)
        far_vec = -np.ones(768, dtype=np.float32)

        storage.store_embedding(t1.id, close_vec, "bge-base-en-v1.5")
        storage.store_embedding(t2.id, far_vec, "bge-base-en-v1.5")

        query = np.ones(768, dtype=np.float32)
        results = storage.find_similar(query, threshold=0.5, limit=10)

        assert len(results) == 1
        assert results[0].trace.id == t1.id

    def test_find_similar_limit(self, storage):
        """Limit caps the number of results returned."""
        for i in range(5):
            t = make_trace(content=f"Trace {i}")
            storage.store_trace(t)
            base = random_embedding()
            # Make all fairly similar to each other
            storage.store_embedding(t.id, base, "bge-base-en-v1.5")

        query = random_embedding()
        results = storage.find_similar(query, threshold=0.0, limit=3)
        assert len(results) <= 3

    def test_find_similar_empty_db(self, storage):
        """No embeddings returns empty list, not an error."""
        query = random_embedding()
        assert storage.find_similar(query) == []

    def test_embedding_cache_appends_on_store(self, storage):
        """Each store_embedding call updates cache without full reload."""
        t1 = make_trace(content="First")
        t2 = make_trace(content="Second")
        storage.store_trace(t1)
        storage.store_trace(t2)

        storage.store_embedding(t1.id, random_embedding(), "bge-base-en-v1.5")
        assert len(storage._embedding_ids) == 1

        storage.store_embedding(t2.id, random_embedding(), "bge-base-en-v1.5")
        assert len(storage._embedding_ids) == 2

    def test_re_embedding_replaces_in_cache(self, storage):
        """Re-embedding a trace updates the vector in-place."""
        trace = make_trace(content="Will be re-embedded")
        storage.store_trace(trace)

        v1 = np.ones(768, dtype=np.float32)
        storage.store_embedding(trace.id, v1, "model-v1")
        assert len(storage._embedding_ids) == 1

        v2 = -np.ones(768, dtype=np.float32)
        storage.store_embedding(trace.id, v2, "model-v2")
        # Still one entry, not two
        assert len(storage._embedding_ids) == 1
        # Cache reflects new vector
        idx = storage._embedding_ids.index(trace.id)
        np.testing.assert_array_almost_equal(
            storage._embedding_matrix[idx],
            v2.astype(np.float32),
        )

    def test_get_all_embeddings(self, storage):
        """Returns copies of cache — caller mutations don't affect storage."""
        t1 = make_trace()
        storage.store_trace(t1)
        emb = random_embedding()
        storage.store_embedding(t1.id, emb, "bge-base-en-v1.5")

        ids, matrix = storage.get_all_embeddings()
        assert len(ids) == 1
        assert ids[0] == t1.id
        assert matrix.shape == (1, 768)

        # Mutating returned copies doesn't affect storage
        ids.append("hacked")
        assert len(storage._embedding_ids) == 1

    def test_get_all_embeddings_empty(self, storage):
        """Empty database returns empty list and empty array."""
        ids, matrix = storage.get_all_embeddings()
        assert ids == []
        assert matrix.shape == (0,)


# ------------------------------------------------------------------
# Annotations
# ------------------------------------------------------------------


class TestAnnotations:
    def make_annotation(self, trace_id: str, **kwargs) -> Annotation:
        defaults = dict(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            type="topic",
            key="rowing",
            value="discussed rowing technique",
            confidence=0.8,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extractor="test-model",
        )
        defaults.update(kwargs)
        return Annotation(**defaults)

    def test_store_and_retrieve_annotation(self, storage):
        """Store an annotation, retrieve by trace ID."""
        trace = make_trace(content="I love rowing")
        storage.store_trace(trace)

        ann = self.make_annotation(trace.id)
        storage.store_annotation(ann)

        annotations = storage.get_annotations_for_trace(trace.id)
        assert len(annotations) == 1
        assert annotations[0].id == ann.id
        assert annotations[0].type == "topic"
        assert annotations[0].key == "rowing"
        assert annotations[0].value == "discussed rowing technique"
        assert annotations[0].confidence == 0.8
        assert annotations[0].extractor == "test-model"

    def test_multiple_annotations_per_trace(self, storage):
        """A trace can have multiple annotations."""
        trace = make_trace(content="I decided to drop rowing and focus on swimming")
        storage.store_trace(trace)

        a1 = self.make_annotation(trace.id, type="decision", key="rowing", value="dropped")
        a2 = self.make_annotation(trace.id, type="commitment", key="swimming", value="new focus")
        storage.store_annotation(a1)
        storage.store_annotation(a2)

        annotations = storage.get_annotations_for_trace(trace.id)
        assert len(annotations) == 2

    def test_get_annotations_by_type(self, storage):
        """Filter annotations across all traces by type."""
        t1 = make_trace(content="Trace 1")
        t2 = make_trace(content="Trace 2")
        storage.store_trace(t1)
        storage.store_trace(t2)

        storage.store_annotation(self.make_annotation(t1.id, type="decision", key="A"))
        storage.store_annotation(self.make_annotation(t1.id, type="emotion", key="B"))
        storage.store_annotation(self.make_annotation(t2.id, type="decision", key="C"))

        decisions = storage.get_annotations_by_type("decision")
        assert len(decisions) == 2
        assert all(a.type == "decision" for a in decisions)

        emotions = storage.get_annotations_by_type("emotion")
        assert len(emotions) == 1

    def test_no_annotations_returns_empty(self, storage):
        """Trace with no annotations returns empty list."""
        trace = make_trace(content="Unannotated")
        storage.store_trace(trace)
        assert storage.get_annotations_for_trace(trace.id) == []

    def test_annotations_ordered_by_extracted_at(self, storage):
        """Annotations returned in extraction order."""
        trace = make_trace(content="Multi-annotation trace")
        storage.store_trace(trace)

        base = datetime(2026, 2, 28, 12, 0, 0, tzinfo=timezone.utc)
        a1 = self.make_annotation(
            trace.id, type="topic", key="first",
            extracted_at=base.isoformat(),
        )
        a2 = self.make_annotation(
            trace.id, type="topic", key="second",
            extracted_at=(base + timedelta(seconds=5)).isoformat(),
        )
        storage.store_annotation(a1)
        storage.store_annotation(a2)

        annotations = storage.get_annotations_for_trace(trace.id)
        assert annotations[0].key == "first"
        assert annotations[1].key == "second"

    def test_annotation_with_null_optional_fields(self, storage):
        """Annotations can have null key, value, confidence."""
        trace = make_trace(content="Vague trace")
        storage.store_trace(trace)

        ann = Annotation(
            id=str(uuid.uuid4()),
            trace_id=trace.id,
            type="topic",
            key=None,
            value=None,
            confidence=None,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extractor="test",
        )
        storage.store_annotation(ann)

        retrieved = storage.get_annotations_for_trace(trace.id)
        assert len(retrieved) == 1
        assert retrieved[0].key is None
        assert retrieved[0].value is None
        assert retrieved[0].confidence is None


# ------------------------------------------------------------------
# Connections
# ------------------------------------------------------------------


class TestConnections:
    def test_store_and_retrieve_connection(self, storage):
        """Store a connection, retrieve by trace ID."""
        t1 = make_trace(content="First")
        t2 = make_trace(content="Second")
        storage.store_trace(t1)
        storage.store_trace(t2)

        conn = Connection(
            source_id=t1.id, target_id=t2.id,
            type="temporal", weight=1.0,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        storage.store_connection(conn)

        # Retrievable from source side
        conns = storage.get_connections_for_trace(t1.id)
        assert len(conns) == 1
        assert conns[0].source_id == t1.id
        assert conns[0].target_id == t2.id
        assert conns[0].type == "temporal"

        # Also retrievable from target side
        conns = storage.get_connections_for_trace(t2.id)
        assert len(conns) == 1

    def test_get_connections_by_type(self, storage):
        """Filter connections by type."""
        t1 = make_trace(content="A")
        t2 = make_trace(content="B")
        t3 = make_trace(content="C")
        storage.store_trace(t1)
        storage.store_trace(t2)
        storage.store_trace(t3)

        now = datetime.now(timezone.utc).isoformat()
        storage.store_connection(Connection(t1.id, t2.id, "temporal", 1.0, now))
        storage.store_connection(Connection(t1.id, t3.id, "semantic", 0.8, now))

        temporal = storage.get_connections_by_type("temporal")
        assert len(temporal) == 1
        assert temporal[0].type == "temporal"

        semantic = storage.get_connections_by_type("semantic")
        assert len(semantic) == 1
        assert semantic[0].type == "semantic"

    def test_delete_connections_by_type(self, storage):
        """Delete all connections of a type, leave others intact."""
        t1 = make_trace(content="A")
        t2 = make_trace(content="B")
        storage.store_trace(t1)
        storage.store_trace(t2)

        now = datetime.now(timezone.utc).isoformat()
        storage.store_connection(Connection(t1.id, t2.id, "temporal", 1.0, now))
        storage.store_connection(Connection(t1.id, t2.id, "semantic", 0.8, now))

        deleted = storage.delete_connections_by_type("semantic")
        assert deleted == 1

        # Temporal still exists
        remaining = storage.get_connections_for_trace(t1.id)
        assert len(remaining) == 1
        assert remaining[0].type == "temporal"

    def test_insert_or_replace_on_same_key(self, storage):
        """Re-storing same (source, target, type) replaces weight."""
        t1 = make_trace(content="A")
        t2 = make_trace(content="B")
        storage.store_trace(t1)
        storage.store_trace(t2)

        now = datetime.now(timezone.utc).isoformat()
        storage.store_connection(Connection(t1.id, t2.id, "semantic", 0.7, now))
        storage.store_connection(Connection(t1.id, t2.id, "semantic", 0.9, now))

        conns = storage.get_connections_by_type("semantic")
        assert len(conns) == 1
        assert conns[0].weight == 0.9

    def test_no_connections_returns_empty(self, storage):
        """Trace with no connections returns empty list."""
        t = make_trace(content="Lonely")
        storage.store_trace(t)
        assert storage.get_connections_for_trace(t.id) == []


# ------------------------------------------------------------------
# Cache initialization
# ------------------------------------------------------------------


class TestCacheInit:
    def test_cache_loads_on_init(self, tmp_path):
        """Embeddings in DB are loaded into cache when storage opens."""
        db_path = tmp_path / "preloaded.db"
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_PATH.read_text())
        # Pre-populate
        trace_id = "preloaded-001"
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO traces (id, timestamp, content, source) VALUES (?, ?, ?, ?)",
            (trace_id, now, "Pre-existing trace", "user"),
        )
        vec = random_embedding()
        conn.execute(
            "INSERT INTO embeddings (trace_id, model, vector, computed_at) VALUES (?, ?, ?, ?)",
            (trace_id, "bge-base-en-v1.5", vec.tobytes(), now),
        )
        conn.commit()
        conn.close()

        # Now open storage — cache should auto-load
        store = SQLiteTraceStorage(db_path)
        assert len(store._embedding_ids) == 1
        assert store._embedding_ids[0] == trace_id
        assert store._embedding_matrix.shape == (1, 768)
        store.close()


# ------------------------------------------------------------------
# Thread structure
# ------------------------------------------------------------------


class TestThreadStructure:
    def test_conversation_thread_via_parent_links(self, storage):
        """Parent links form a conversation thread: user→assistant→user."""
        base_time = datetime(2026, 2, 28, 12, 0, 0, tzinfo=timezone.utc)

        t1 = make_trace(
            content="What should I focus on?",
            source="user",
            conversation_id="conv-thread",
            timestamp=base_time.isoformat(),
        )
        storage.store_trace(t1)

        t2 = make_trace(
            content="Based on your goals, I'd suggest...",
            source="assistant",
            conversation_id="conv-thread",
            parent_trace_id=t1.id,
            timestamp=(base_time + timedelta(seconds=5)).isoformat(),
        )
        storage.store_trace(t2)

        t3 = make_trace(
            content="That makes sense, but what about rowing?",
            source="user",
            conversation_id="conv-thread",
            parent_trace_id=t2.id,
            timestamp=(base_time + timedelta(seconds=30)).isoformat(),
        )
        storage.store_trace(t3)

        # Walk the chain
        trace3 = storage.get_trace(t3.id)
        trace2 = storage.get_trace(trace3.parent_trace_id)
        trace1 = storage.get_trace(trace2.parent_trace_id)

        assert trace3.content == "That makes sense, but what about rowing?"
        assert trace2.content == "Based on your goals, I'd suggest..."
        assert trace1.content == "What should I focus on?"
        assert trace1.parent_trace_id is None  # Root of thread
