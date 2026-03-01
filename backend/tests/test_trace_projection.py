"""
Tests for trace projection service.

Uses real embeddings to verify UMAP, DBSCAN, and k-NN produce
valid output shapes and reasonable values.
"""

import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace, Annotation
from services.trace_projection import compute_trace_projection


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


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


def seed_traces(storage, n=20):
    """Create n traces with random embeddings, spread over 2 conversations."""
    now = datetime.now(timezone.utc)
    traces = []
    parent_id = None
    for i in range(n):
        conv_id = "conv-A" if i < n // 2 else "conv-B"
        if i == n // 2:
            parent_id = None  # Reset parent for second conversation

        t = Trace(
            id=str(uuid.uuid4()),
            timestamp=(now - timedelta(days=n - i)).isoformat(),
            content=f"Trace message {i} about topic {'alpha' if i % 3 == 0 else 'beta' if i % 3 == 1 else 'gamma'}",
            conversation_id=conv_id,
            parent_trace_id=parent_id,
            source="user" if i % 2 == 0 else "assistant",
        )
        storage.store_trace(t)

        # Create embeddings that cluster: similar content → similar vectors
        base = np.zeros(768, dtype=np.float32)
        base[i % 3 * 100:(i % 3 + 1) * 100] = 1.0  # 3 cluster-like groups
        noise = np.random.randn(768).astype(np.float32) * 0.1
        emb = base + noise
        emb = emb / (np.linalg.norm(emb) + 1e-10)
        storage.store_embedding(t.id, emb, "test")

        parent_id = t.id
        traces.append(t)
    return traces


# ------------------------------------------------------------------
# Projection output shape
# ------------------------------------------------------------------


class TestProjectionOutput:
    def test_empty_storage_returns_empty(self, storage):
        result = compute_trace_projection(storage)
        assert result["nodes"] == []
        assert result["clusters"] == []
        assert result["edges"] == []
        assert result["meta"]["count"] == 0

    def test_returns_correct_node_count(self, storage):
        seed_traces(storage, n=15)
        result = compute_trace_projection(storage)
        assert result["meta"]["count"] == 15
        assert len(result["nodes"]) == 15

    def test_node_has_required_fields(self, storage):
        seed_traces(storage, n=10)
        result = compute_trace_projection(storage)
        node = result["nodes"][0]

        required_fields = [
            "id", "label", "fullText", "source", "conversationId",
            "createdAt", "age", "position", "positionTime",
            "keywords", "cluster", "annotations",
        ]
        for field in required_fields:
            assert field in node, f"Missing field: {field}"

    def test_position_is_3d_array(self, storage):
        seed_traces(storage, n=10)
        result = compute_trace_projection(storage)
        node = result["nodes"][0]

        assert len(node["position"]) == 3
        assert len(node["positionTime"]) == 3
        assert all(isinstance(v, float) for v in node["position"])

    def test_age_normalized_zero_to_one(self, storage):
        seed_traces(storage, n=10)
        result = compute_trace_projection(storage)

        ages = [n["age"] for n in result["nodes"]]
        assert min(ages) >= 0.0
        assert max(ages) <= 1.0

    def test_source_preserved(self, storage):
        seed_traces(storage, n=10)
        result = compute_trace_projection(storage)

        sources = {n["source"] for n in result["nodes"]}
        assert "user" in sources
        assert "assistant" in sources

    def test_conversation_id_preserved(self, storage):
        seed_traces(storage, n=20)
        result = compute_trace_projection(storage)

        conv_ids = {n["conversationId"] for n in result["nodes"]}
        assert "conv-A" in conv_ids
        assert "conv-B" in conv_ids


# ------------------------------------------------------------------
# Clustering
# ------------------------------------------------------------------


class TestClustering:
    def test_clusters_have_required_fields(self, storage):
        seed_traces(storage, n=20)
        result = compute_trace_projection(storage)

        if result["clusters"]:
            cluster = result["clusters"][0]
            assert "id" in cluster
            assert "center" in cluster
            assert "radius" in cluster
            assert "count" in cluster
            assert "label" in cluster
            assert len(cluster["center"]) == 3

    def test_cluster_count_matches_meta(self, storage):
        seed_traces(storage, n=20)
        result = compute_trace_projection(storage)
        assert len(result["clusters"]) == result["meta"].get("n_clusters", 0)


# ------------------------------------------------------------------
# Edges
# ------------------------------------------------------------------


class TestEdges:
    def test_edges_have_required_fields(self, storage):
        seed_traces(storage, n=10)
        result = compute_trace_projection(storage)

        if result["edges"]:
            edge = result["edges"][0]
            assert "source" in edge
            assert "target" in edge
            assert "weight" in edge
            assert 0 < edge["weight"] <= 1.0

    def test_edge_ids_reference_real_traces(self, storage):
        traces = seed_traces(storage, n=10)
        result = compute_trace_projection(storage)

        trace_ids = {t.id for t in traces}
        for edge in result["edges"]:
            assert edge["source"] in trace_ids
            assert edge["target"] in trace_ids

    def test_no_self_edges(self, storage):
        seed_traces(storage, n=10)
        result = compute_trace_projection(storage)

        for edge in result["edges"]:
            assert edge["source"] != edge["target"]


# ------------------------------------------------------------------
# Annotations in projection
# ------------------------------------------------------------------


class TestAnnotationsInProjection:
    def test_annotations_included_on_nodes(self, storage):
        """Traces with annotations include them in projection output."""
        traces = seed_traces(storage, n=5)

        # Add an annotation to the first trace
        ann = Annotation(
            id=str(uuid.uuid4()),
            trace_id=traces[0].id,
            type="decision",
            key="career",
            value="chose AI engineering",
            confidence=0.9,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extractor="test",
        )
        storage.store_annotation(ann)

        result = compute_trace_projection(storage)

        # Find the annotated node
        annotated = [n for n in result["nodes"] if n["id"] == traces[0].id]
        assert len(annotated) == 1
        assert len(annotated[0]["annotations"]) == 1
        assert annotated[0]["annotations"][0]["type"] == "decision"

    def test_unannotated_traces_have_empty_list(self, storage):
        seed_traces(storage, n=5)
        result = compute_trace_projection(storage)

        for node in result["nodes"]:
            assert isinstance(node["annotations"], list)


# ------------------------------------------------------------------
# Small N edge cases
# ------------------------------------------------------------------


class TestSmallN:
    def test_single_trace(self, storage):
        """One trace should produce one node, no edges, no clusters."""
        t = Trace(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            content="Only trace",
            conversation_id="conv-solo",
            source="user",
        )
        storage.store_trace(t)
        emb = np.random.randn(768).astype(np.float32)
        storage.store_embedding(t.id, emb, "test")

        result = compute_trace_projection(storage)
        assert len(result["nodes"]) == 1
        assert len(result["edges"]) == 0

    def test_two_traces(self, storage):
        """Two traces produce nodes and potentially one edge."""
        for i in range(2):
            t = Trace(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                content=f"Trace {i}",
                conversation_id="conv-pair",
                source="user",
            )
            storage.store_trace(t)
            emb = np.ones(768, dtype=np.float32) * (1 + i * 0.01)
            storage.store_embedding(t.id, emb, "test")

        result = compute_trace_projection(storage)
        assert len(result["nodes"]) == 2
