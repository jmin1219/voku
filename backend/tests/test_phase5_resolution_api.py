"""
Tests for Phase 5 resolution-aware API endpoint (Task 5.7).

/api/phase-space returns traces, clusters, orientations, edges, meta
in a single response that the frontend can consume at any resolution level.
"""

import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace
from services.trace_projection import compute_trace_projection


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_api.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    s = SQLiteTraceStorage(db_path)
    yield s
    s.close()


def seed(storage, n=15):
    now = datetime.now(timezone.utc)
    for i in range(n):
        t = Trace(
            id=str(uuid.uuid4()),
            timestamp=(now - timedelta(days=n - i)).isoformat(),
            content=f"Trace {i} about {'coding' if i % 2 == 0 else 'fitness'}",
            conversation_id=f"conv-{i % 3}",
            source="user" if i % 2 == 0 else "assistant",
        )
        storage.store_trace(t)
        base = np.zeros(768, dtype=np.float32)
        base[(i % 2) * 200:(i % 2 + 1) * 200] = 1.0
        noise = np.random.randn(768).astype(np.float32) * 0.1
        emb = base + noise
        emb /= np.linalg.norm(emb) + 1e-10
        storage.store_embedding(t.id, emb, "test")


class TestResolutionAPI:
    def test_returns_all_sections(self, storage):
        """Response contains traces, clusters, orientations, edges, meta."""
        seed(storage)
        result = compute_trace_projection(storage)

        assert "nodes" in result
        assert "clusters" in result
        assert "orientations" in result
        assert "edges" in result
        assert "meta" in result

    def test_every_trace_has_cluster_and_orientation(self, storage):
        """Each node carries both cluster and orientation IDs."""
        seed(storage)
        result = compute_trace_projection(storage)

        for node in result["nodes"]:
            assert "cluster" in node, f"Node {node['id']} missing cluster"
            assert "orientation" in node, f"Node {node['id']} missing orientation"
            assert isinstance(node["cluster"], int)
            assert isinstance(node["orientation"], int)

    def test_every_cluster_has_orientation_id(self, storage):
        """Each cluster links to an orientation."""
        seed(storage)
        result = compute_trace_projection(storage)

        for cluster in result["clusters"]:
            assert "orientation_id" in cluster
            assert isinstance(cluster["orientation_id"], int)

    def test_every_orientation_has_cluster_ids(self, storage):
        """Each orientation lists its constituent cluster IDs."""
        seed(storage)
        result = compute_trace_projection(storage)

        for orient in result["orientations"]:
            assert "label" in orient
            assert "cluster_ids" in orient
            assert isinstance(orient["cluster_ids"], list)
            assert "trace_count" in orient

    def test_empty_database_returns_valid_structure(self, storage):
        """Empty DB returns 200-equivalent valid structure, not error."""
        result = compute_trace_projection(storage)

        assert result["nodes"] == []
        assert result["clusters"] == []
        assert result["orientations"] == []
        assert result["edges"] == []
        assert result["meta"]["count"] == 0

    def test_json_serializable(self, storage):
        """No numpy types leak into the response."""
        import json
        seed(storage)
        result = compute_trace_projection(storage)

        # This will raise TypeError if numpy types leak
        serialized = json.dumps(result)
        assert len(serialized) > 0

    def test_clusters_have_trace_ids(self, storage):
        """Each cluster includes its member trace IDs."""
        seed(storage)
        result = compute_trace_projection(storage)

        for cluster in result["clusters"]:
            assert "trace_ids" in cluster
            assert isinstance(cluster["trace_ids"], list)
            assert cluster["count"] == len(cluster["trace_ids"])
