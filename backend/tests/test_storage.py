"""
Tests for SQLite storage layer.

Component 1.2 in COMPONENT_SPEC.md.
"""

from datetime import datetime

import numpy as np
import pytest

from services.storage.sqlite_storage import SQLiteStorage
from services.storage.models import StoredProposition


@pytest.fixture
def storage(tmp_path):
    """Create a fresh SQLite storage in a temp directory."""
    db = SQLiteStorage(tmp_path / "test.db")
    yield db
    db.close()


@pytest.fixture
def sample_proposition():
    """A reusable test proposition."""
    return StoredProposition(
        id="test-uuid-001",
        text="I think my ankle limits my rowing performance",
        node_type="belief",
        confidence=0.95,
        source_type="conversation",
        created_at="2026-02-10T21:53:12",
        session_id="session-abc",
        message_index=0,
        source_char_start=100,
        source_char_end=200,
        source_file="Deep Research on Voku Plans.md",
    )


def test_store_and_retrieve_proposition(storage, sample_proposition):
    stored_id = storage.store_proposition(sample_proposition)
    assert stored_id == "test-uuid-001"

    results = storage.find_by_session("session-abc")
    assert len(results) == 1
    assert results[0].text == "I think my ankle limits my rowing performance"
    assert results[0].node_type == "belief"
    assert results[0].confidence == 0.95
    assert results[0].source_file == "Deep Research on Voku Plans.md"


def test_store_embedding_and_find_similar(storage, sample_proposition):
    storage.store_proposition(sample_proposition)

    embedding = np.random.randn(768).astype(np.float32)
    embedding = embedding / np.linalg.norm(embedding)
    storage.store_embedding("test-uuid-001", embedding, "bge-base-en-v1.5")

    results = storage.find_similar(embedding, threshold=0.9)
    assert len(results) == 1
    assert results[0].proposition.id == "test-uuid-001"
    assert results[0].score > 0.99


def test_find_similar_below_threshold_returns_empty(storage, sample_proposition):
    storage.store_proposition(sample_proposition)

    embedding = np.random.randn(768).astype(np.float32)
    storage.store_embedding("test-uuid-001", embedding, "bge-base-en-v1.5")

    query = np.random.randn(768).astype(np.float32)
    results = storage.find_similar(query, threshold=0.99)
    assert len(results) == 0


def test_find_by_timerange(storage):
    p1 = StoredProposition(
        id="p1", text="Morning belief", node_type="belief",
        confidence=0.9, source_type="conversation",
        created_at="2026-02-10T08:00:00",
    )
    p2 = StoredProposition(
        id="p2", text="Evening belief", node_type="observation",
        confidence=0.85, source_type="conversation",
        created_at="2026-02-10T20:00:00",
    )
    p3 = StoredProposition(
        id="p3", text="Next day belief", node_type="belief",
        confidence=1.0, source_type="conversation",
        created_at="2026-02-11T10:00:00",
    )
    storage.store_proposition(p1)
    storage.store_proposition(p2)
    storage.store_proposition(p3)

    results = storage.find_by_timerange(
        datetime(2026, 2, 10, 0, 0),
        datetime(2026, 2, 10, 23, 59),
    )
    assert len(results) == 2
    assert results[0].id == "p1"
    assert results[1].id == "p2"


def test_find_by_session(storage):
    p1 = StoredProposition(
        id="p1", text="First message", node_type="observation",
        confidence=0.8, source_type="conversation",
        created_at="2026-02-10T08:00:00", session_id="sess-1", message_index=0,
    )
    p2 = StoredProposition(
        id="p2", text="Second message", node_type="belief",
        confidence=0.95, source_type="conversation",
        created_at="2026-02-10T08:01:00", session_id="sess-1", message_index=1,
    )
    p3 = StoredProposition(
        id="p3", text="Different session", node_type="decision",
        confidence=1.0, source_type="conversation",
        created_at="2026-02-10T09:00:00", session_id="sess-2", message_index=0,
    )
    storage.store_proposition(p1)
    storage.store_proposition(p2)
    storage.store_proposition(p3)

    results = storage.find_by_session("sess-1")
    assert len(results) == 2
    assert results[0].message_index == 0
    assert results[1].message_index == 1


def test_get_all_embeddings_shape(storage, sample_proposition):
    storage.store_proposition(sample_proposition)

    emb = np.random.randn(768).astype(np.float32)
    storage.store_embedding("test-uuid-001", emb, "bge-base-en-v1.5")

    ids, matrix = storage.get_all_embeddings()
    assert len(ids) == 1
    assert matrix.shape == (1, 768)


def test_empty_database_returns_empty(storage):
    assert storage.find_by_session("nonexistent") == []
    assert storage.find_similar(np.random.randn(768).astype(np.float32)) == []
    ids, matrix = storage.get_all_embeddings()
    assert len(ids) == 0


def test_database_is_single_file(tmp_path):
    db_path = tmp_path / "portable.db"
    db = SQLiteStorage(db_path)
    db.store_proposition(StoredProposition(
        id="p1", text="Test", node_type="belief",
        confidence=0.9, source_type="conversation",
        created_at="2026-02-10T08:00:00",
    ))
    db.close()

    assert db_path.exists()
    db2 = SQLiteStorage(db_path)
    results = db2.find_by_timerange(datetime(2026, 1, 1), datetime(2026, 12, 31))
    assert results[0].text == "Test"
    db2.close()
