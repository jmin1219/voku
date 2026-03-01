"""
Tests for Phase 5 cluster metadata generation (Task 5.6).

LLM generates 3-5 word labels and 1-sentence summaries for each cluster
using the top-5 most central traces. Falls back to keyword extraction
when LLM is unavailable.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from services.storage.sqlite_trace import SQLiteTraceStorage
from services.storage.models import Trace
from services.embedding.bge import BGEBaseEmbedding
from services.cluster_metadata import ClusterMetadataService, ClusterMeta


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


class MockLabelProvider:
    """Returns a label/summary JSON for cluster labeling."""

    def __init__(self, response=None):
        self.response = response or json.dumps({
            "label": "AI Engineering Career",
            "summary": "Traces about pursuing AI engineering as a career direction."
        })
        self.call_count = 0

    async def complete(self, prompt, *, system_prompt=None, model=None, max_tokens=None):
        self.call_count += 1
        return self.response

    async def vision(self, image_base64, prompt):
        return ""


class FailingLabelProvider:
    async def complete(self, prompt, *, system_prompt=None, model=None, max_tokens=None):
        raise Exception("LLM down")

    async def vision(self, image_base64, prompt):
        return ""


@pytest.fixture(scope="module")
def real_embedder():
    return BGEBaseEmbedding()


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_metadata.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    s = SQLiteTraceStorage(db_path)
    yield s
    s.close()


def store_and_embed(storage, embedder, content):
    t = Trace(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        content=content,
        conversation_id="conv-001",
        source="user",
    )
    storage.store_trace(t)
    emb = embedder.embed(content)
    storage.store_embedding(t.id, emb, embedder.model_name)
    return t


class TestClusterMetadataGeneration:
    @pytest.mark.asyncio
    async def test_generates_label_and_summary(self, storage, real_embedder):
        """Each cluster gets a label and summary from LLM."""
        traces = []
        for msg in [
            "Building a FastAPI backend for the project",
            "FastAPI automatic OpenAPI documentation is useful",
            "Python backend with SQLite for single-file storage",
        ]:
            traces.append(store_and_embed(storage, real_embedder, msg))

        embeddings = {t.id: real_embedder.embed(t.content) for t in traces}

        # Fake cluster: all traces in cluster 0
        clusters = [{"id": 0, "trace_ids": [t.id for t in traces]}]

        provider = MockLabelProvider()
        service = ClusterMetadataService(provider)
        results = await service.generate_labels(clusters, traces, embeddings)

        assert len(results) == 1
        assert results[0].label == "AI Engineering Career"
        assert "career" in results[0].summary.lower() or len(results[0].summary) > 0
        assert results[0].cluster_id == 0

    @pytest.mark.asyncio
    async def test_central_traces_selected_by_embedding_distance(self, storage, real_embedder):
        """Central traces are closest to centroid, not random."""
        traces = []
        for msg in [
            "React hooks for state management in components",
            "useState and useEffect are the most common React hooks",
            "React component lifecycle with functional hooks pattern",
            "Building React apps with TypeScript and Tailwind",
            "CSS-in-JS vs Tailwind for React styling approaches",
            "Server-side rendering with Next.js and React",
            "The weather in Vancouver is rainy this week",  # outlier
        ]:
            traces.append(store_and_embed(storage, real_embedder, msg))

        embeddings = {t.id: real_embedder.embed(t.content) for t in traces}
        clusters = [{"id": 0, "trace_ids": [t.id for t in traces]}]

        provider = MockLabelProvider()
        service = ClusterMetadataService(provider)
        results = await service.generate_labels(clusters, traces, embeddings)

        assert len(results) == 1
        # The prompt sent to LLM should contain the central traces
        assert results[0].central_trace_ids is not None
        assert len(results[0].central_trace_ids) <= 5
        # Weather outlier should NOT be in central traces
        weather_id = traces[-1].id
        assert weather_id not in results[0].central_trace_ids

    @pytest.mark.asyncio
    async def test_falls_back_to_keywords_on_llm_failure(self, storage, real_embedder):
        """When LLM fails, label falls back to keyword extraction."""
        traces = []
        for msg in [
            "Machine learning model training pipeline",
            "PyTorch neural network gradient optimization",
            "Deep learning hyperparameter tuning strategies",
        ]:
            traces.append(store_and_embed(storage, real_embedder, msg))

        embeddings = {t.id: real_embedder.embed(t.content) for t in traces}
        clusters = [{"id": 0, "trace_ids": [t.id for t in traces]}]

        service = ClusterMetadataService(FailingLabelProvider())
        results = await service.generate_labels(clusters, traces, embeddings)

        assert len(results) == 1
        # Should have a keyword-based label, not empty
        assert len(results[0].label) > 0
        assert results[0].summary == ""  # No summary without LLM

    @pytest.mark.asyncio
    async def test_small_cluster_uses_keyword_fallback(self, storage, real_embedder):
        """Clusters with < 3 traces skip LLM, use keyword extraction."""
        traces = [store_and_embed(storage, real_embedder, "Just one trace about rowing")]
        embeddings = {t.id: real_embedder.embed(t.content) for t in traces}
        clusters = [{"id": 0, "trace_ids": [t.id for t in traces]}]

        provider = MockLabelProvider()
        service = ClusterMetadataService(provider)
        results = await service.generate_labels(clusters, traces, embeddings)

        assert len(results) == 1
        assert provider.call_count == 0  # LLM not called for tiny cluster

    @pytest.mark.asyncio
    async def test_multiple_clusters_independently(self, storage, real_embedder):
        """LLM failure on one cluster doesn't break others."""
        traces_a = [store_and_embed(storage, real_embedder, f"Cluster A trace {i}") for i in range(3)]
        traces_b = [store_and_embed(storage, real_embedder, f"Cluster B trace {i}") for i in range(3)]

        all_traces = traces_a + traces_b
        embeddings = {t.id: real_embedder.embed(t.content) for t in all_traces}
        clusters = [
            {"id": 0, "trace_ids": [t.id for t in traces_a]},
            {"id": 1, "trace_ids": [t.id for t in traces_b]},
        ]

        call_count = 0

        class FailOnSecondProvider:
            async def complete(self, prompt, **kw):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise Exception("Fail on cluster 1")
                return json.dumps({"label": "Cluster A Label", "summary": "Summary A."})

            async def vision(self, *a):
                return ""

        service = ClusterMetadataService(FailOnSecondProvider())
        results = await service.generate_labels(clusters, all_traces, embeddings)

        assert len(results) == 2
        assert results[0].label == "Cluster A Label"
        # Second cluster should have keyword fallback
        assert len(results[1].label) > 0

    @pytest.mark.asyncio
    async def test_empty_clusters_returns_empty(self, storage, real_embedder):
        """No clusters produces no metadata."""
        service = ClusterMetadataService(MockLabelProvider())
        results = await service.generate_labels([], [], {})
        assert results == []
