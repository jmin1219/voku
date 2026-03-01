"""
Tests for Phase 5 hierarchical clustering (Task 5.5).

Two-level clustering on embedding space (not UMAP positions):
  - Fine clusters: DBSCAN eps=0.3, min_samples=3
  - Orientations: DBSCAN eps=0.6 on fine cluster centroids
"""

import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace
from services.embedding.bge import BGEBaseEmbedding
from services.trace_projection import compute_trace_projection


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


@pytest.fixture(scope="module")
def real_embedder():
    return BGEBaseEmbedding()


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_clustering.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    s = SQLiteTraceStorage(db_path)
    yield s
    s.close()


def store_and_embed(storage, embedder, content, conversation_id="conv-001", timestamp=None):
    t = Trace(
        id=str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        content=content,
        conversation_id=conversation_id,
        source="user",
    )
    storage.store_trace(t)
    emb = embedder.embed(content)
    storage.store_embedding(t.id, emb, embedder.model_name)
    return t


class TestHierarchicalClustering:
    def test_produces_fine_clusters(self, storage, real_embedder):
        """Fine clustering at eps=0.3 produces clusters from semantically grouped traces."""
        # Group 1: AI/ML topic
        for msg in [
            "Building a machine learning pipeline with PyTorch",
            "Training neural networks requires careful hyperparameter tuning",
            "Deep learning frameworks like TensorFlow and PyTorch dominate",
            "Gradient descent optimization in neural network training",
        ]:
            store_and_embed(storage, real_embedder, msg)

        # Group 2: cooking topic
        for msg in [
            "Making sourdough bread requires a good starter culture",
            "The fermentation process for sourdough takes at least 12 hours",
            "Baking bread at the right temperature is crucial for crust",
            "My sourdough recipe uses whole wheat flour and sea salt",
        ]:
            store_and_embed(storage, real_embedder, msg)

        # Group 3: exercise topic
        for msg in [
            "Rowing on the ergometer builds cardiovascular endurance",
            "The 2K rowing test measures anaerobic power and aerobic capacity",
            "Indoor rowing technique focuses on leg drive and hip hinge",
            "Heart rate zones during rowing intervals vary between Z2 and Z4",
        ]:
            store_and_embed(storage, real_embedder, msg)

        result = compute_trace_projection(storage)

        assert len(result["clusters"]) >= 2, \
            f"Expected at least 2 fine clusters from 3 distinct topics, got {len(result['clusters'])}"

    def test_produces_orientations(self, storage, real_embedder):
        """Orientation-level clustering produces broader groupings than fine clusters."""
        # Same setup: 3 clear topic groups
        topics = {
            "ai": [
                "Machine learning model evaluation metrics",
                "Cross-validation prevents overfitting in ML",
                "Feature engineering for tabular data in scikit-learn",
                "Random forest classifier performance tuning",
            ],
            "fitness": [
                "Progressive overload is fundamental to strength training",
                "Periodization alternates volume and intensity phases",
                "Recovery between training sessions matters for adaptation",
                "Heart rate variability tracks autonomic nervous system recovery",
            ],
            "cooking": [
                "Cast iron skillets need proper seasoning maintenance",
                "Deglazing a pan creates the foundation for a great sauce",
                "Maillard reaction requires high heat and dry surfaces",
                "Resting meat after cooking redistributes the juices evenly",
            ],
        }
        for topic, messages in topics.items():
            for msg in messages:
                store_and_embed(storage, real_embedder, msg, conversation_id=f"conv-{topic}")

        result = compute_trace_projection(storage)

        assert "orientations" in result, "Response must include orientations"
        # Orientations should be fewer than fine clusters
        if len(result["clusters"]) > 0 and len(result["orientations"]) > 0:
            assert len(result["orientations"]) <= len(result["clusters"]), \
                "Orientations should be coarser than fine clusters"

    def test_fine_clusters_link_to_orientation(self, storage, real_embedder):
        """Every fine cluster maps to exactly one orientation (or -1 noise)."""
        for i in range(12):
            store_and_embed(storage, real_embedder, f"Trace about topic {i % 3} variation {i}")

        result = compute_trace_projection(storage)

        for cluster in result["clusters"]:
            assert "orientation_id" in cluster, "Each fine cluster must have orientation_id"
            assert isinstance(cluster["orientation_id"], int)

    def test_traces_have_cluster_and_orientation(self, storage, real_embedder):
        """Every node in the response has both cluster and orientation IDs."""
        for i in range(6):
            store_and_embed(storage, real_embedder, f"Test trace number {i} about software")

        result = compute_trace_projection(storage)

        for node in result["nodes"]:
            assert "cluster" in node
            assert "orientation" in node

    def test_noise_traces_handled(self, storage, real_embedder):
        """Traces not assigned to any cluster get cluster=-1, still render."""
        # Just 2 very different traces — too few for DBSCAN to cluster
        store_and_embed(storage, real_embedder, "Quantum computing research paper")
        store_and_embed(storage, real_embedder, "My favorite breakfast cereal brand")
        store_and_embed(storage, real_embedder, "The weather in Vancouver today")

        result = compute_trace_projection(storage)

        assert len(result["nodes"]) == 3
        # Some or all may be noise (-1) — that's fine
        for node in result["nodes"]:
            assert "cluster" in node

    def test_fewer_than_three_traces(self, storage, real_embedder):
        """Graceful handling with too few traces for UMAP/DBSCAN."""
        store_and_embed(storage, real_embedder, "Only one trace")

        result = compute_trace_projection(storage)

        assert len(result["nodes"]) == 1
        assert len(result["clusters"]) == 0
        assert len(result.get("orientations", [])) == 0

    def test_clustering_on_embeddings_not_umap(self, storage, real_embedder):
        """Clustering uses 768d embedding space, not 3d UMAP positions.

        Verified by: fine clusters at eps=0.3 would produce nothing useful
        on UMAP positions (which are scaled to [-5, 5]), but work on
        normalized 768d embeddings where cosine distances are small.
        """
        # 6 traces about the same narrow topic — should cluster in embedding space
        for msg in [
            "React hooks useState and useEffect lifecycle",
            "React functional components with hooks pattern",
            "useState hook manages local component state in React",
            "useEffect hook handles side effects in React components",
            "React component re-rendering triggered by state changes",
            "Managing React state with useReducer for complex logic",
        ]:
            store_and_embed(storage, real_embedder, msg)

        result = compute_trace_projection(storage)

        # These are semantically tight — should form at least 1 cluster
        assert len(result["clusters"]) >= 1, \
            "Tightly related traces should cluster in embedding space"
