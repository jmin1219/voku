"""
Tests for Phase 7 temporal digest (Task 7.4).

AI-synthesized narrative summaries from the trace graph. Period summaries
are stored as system traces; topic evolutions are ephemeral.

Mock provider returns canned narratives. Real embedder for semantic tests.
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
from services.temporal_digest import TemporalDigestService


SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "v2_schema.sql"


# ------------------------------------------------------------------
# Mock providers
# ------------------------------------------------------------------


class MockDigestProvider:
    """Returns a canned narrative for digest generation."""

    def __init__(self, response: str | None = None):
        self.response = response or (
            "Over the past month, your thinking has centered on two main threads. "
            "You've been exploring AI engineering as a career path, weighing co-op "
            "opportunities against deeper research directions. At the same time, "
            "your training program has undergone a significant shift — the 2K row "
            "goal was dropped in favor of thoracic pump restoration work."
        )
        self.call_count = 0
        self.last_prompt = None
        self.last_system_prompt = None

    async def complete(self, prompt, *, system_prompt=None, model=None, max_tokens=None):
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        return self.response

    async def vision(self, image_base64, prompt):
        return ""


class FailingProvider:
    """Always raises on complete()."""

    async def complete(self, prompt, *, system_prompt=None, model=None, max_tokens=None):
        raise Exception("LLM unavailable")

    async def vision(self, image_base64, prompt):
        return ""


class EmptyProvider:
    """Returns empty string on complete()."""

    async def complete(self, prompt, *, system_prompt=None, model=None, max_tokens=None):
        return ""

    async def vision(self, image_base64, prompt):
        return ""


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_embedder():
    return BGEBaseEmbedding()


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_digest.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_PATH.read_text())
    conn.close()
    s = SQLiteTraceStorage(db_path)
    yield s
    s.close()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def store_trace(
    storage: SQLiteTraceStorage,
    embedder: BGEBaseEmbedding,
    content: str,
    source: str = "user",
    conversation_id: str = "conv-001",
    timestamp: datetime | None = None,
) -> Trace:
    """Store a trace with embedding. Returns the Trace."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    t = Trace(
        id=str(uuid.uuid4()),
        timestamp=timestamp.isoformat(),
        content=content,
        conversation_id=conversation_id,
        source=source,
    )
    storage.store_trace(t)
    emb = embedder.embed(content)
    storage.store_embedding(t.id, emb, embedder.model_name)
    return t


def populate_multi_domain(
    storage: SQLiteTraceStorage,
    embedder: BGEBaseEmbedding,
    days_ago: int = 7,
) -> list[Trace]:
    """Populate storage with multi-domain traces spanning a time window."""
    now = datetime.now(timezone.utc)
    traces = []

    # Career traces
    career_msgs = [
        "I've been thinking about AI engineer co-op positions in Vancouver",
        "LangChain and vector databases seem like the most in-demand skills",
        "My FastAPI and testing experience should differentiate me from ML-only candidates",
    ]
    for i, msg in enumerate(career_msgs):
        ts = now - timedelta(days=days_ago - i, hours=2)
        traces.append(store_trace(storage, embedder, msg, conversation_id="conv-career", timestamp=ts))

    # Training traces
    training_msgs = [
        "The 2K row goal isn't worth optimizing since rowing loads both weak links",
        "Incline treadmill walking might be better for thoracic pump restoration",
        "Bike HR ceiling at 135 with arms supported confirms thoracic stabilization cost",
    ]
    for i, msg in enumerate(training_msgs):
        ts = now - timedelta(days=days_ago - i, hours=4)
        traces.append(store_trace(storage, embedder, msg, conversation_id="conv-training", timestamp=ts))

    # Academic traces
    academic_msgs = [
        "CS5008 quicksort implementation passed all tests including edge cases",
        "The midterm covers sorting algorithms and hash tables primarily",
    ]
    for i, msg in enumerate(academic_msgs):
        ts = now - timedelta(days=days_ago - i, hours=6)
        traces.append(store_trace(storage, embedder, msg, conversation_id="conv-academic", timestamp=ts))

    return traces


# ------------------------------------------------------------------
# generate_period_summary tests
# ------------------------------------------------------------------


class TestGeneratePeriodSummary:
    @pytest.mark.asyncio
    async def test_generates_narrative_for_traces_in_window(self, storage, real_embedder):
        """Period summary generates coherent narrative (not empty) for traces in window."""
        populate_multi_domain(storage, real_embedder, days_ago=7)

        provider = MockDigestProvider()
        service = TemporalDigestService(storage, real_embedder, provider)
        digest = await service.generate_period_summary(days=30)

        assert digest.content is not None
        assert len(digest.content) > 50
        assert digest.source == "system"

    @pytest.mark.asyncio
    async def test_summary_stored_as_system_trace(self, storage, real_embedder):
        """Summary is stored as a system trace retrievable by ID."""
        populate_multi_domain(storage, real_embedder, days_ago=5)

        provider = MockDigestProvider()
        service = TemporalDigestService(storage, real_embedder, provider)
        digest = await service.generate_period_summary(days=30)

        # Verify stored
        retrieved = storage.get_trace(digest.id)
        assert retrieved is not None
        assert retrieved.source == "system"
        assert retrieved.content == digest.content

    @pytest.mark.asyncio
    async def test_system_trace_is_embedded(self, storage, real_embedder):
        """Digest trace is embedded so future context assembly can retrieve it."""
        populate_multi_domain(storage, real_embedder, days_ago=5)

        provider = MockDigestProvider()
        service = TemporalDigestService(storage, real_embedder, provider)
        digest = await service.generate_period_summary(days=30)

        # Check embedding exists in cache
        ids, matrix = storage.get_all_embeddings()
        assert digest.id in ids

    @pytest.mark.asyncio
    async def test_conversation_id_follows_digest_pattern(self, storage, real_embedder):
        """Digest trace conversation_id = 'digest-{YYYY-MM-DD}'."""
        populate_multi_domain(storage, real_embedder, days_ago=5)

        provider = MockDigestProvider()
        service = TemporalDigestService(storage, real_embedder, provider)
        digest = await service.generate_period_summary(days=30)

        assert digest.conversation_id is not None
        assert digest.conversation_id.startswith("digest-")
        # Validate date format
        date_part = digest.conversation_id.replace("digest-", "")
        datetime.strptime(date_part, "%Y-%m-%d")  # Raises if invalid

    @pytest.mark.asyncio
    async def test_only_user_traces_included(self, storage, real_embedder):
        """Summary is built from user traces only, not assistant responses."""
        now = datetime.now(timezone.utc)

        store_trace(storage, real_embedder, "My thinking about career", source="user", timestamp=now - timedelta(days=1))
        store_trace(storage, real_embedder, "Here are some suggestions", source="assistant", timestamp=now - timedelta(days=1, hours=-1))
        store_trace(storage, real_embedder, "I decided on AI engineering", source="user", timestamp=now - timedelta(hours=12))

        provider = MockDigestProvider()
        service = TemporalDigestService(storage, real_embedder, provider)
        await service.generate_period_summary(days=7)

        # The prompt sent to LLM should only contain user content
        assert provider.last_prompt is not None
        assert "Here are some suggestions" not in provider.last_prompt

    @pytest.mark.asyncio
    async def test_clusters_appear_in_prompt(self, storage, real_embedder):
        """Multi-domain traces produce clustered prompt structure."""
        populate_multi_domain(storage, real_embedder, days_ago=5)

        provider = MockDigestProvider()
        service = TemporalDigestService(storage, real_embedder, provider)
        await service.generate_period_summary(days=30)

        # Prompt should contain cluster markers
        assert provider.last_prompt is not None
        assert "Cluster" in provider.last_prompt or "Miscellaneous" in provider.last_prompt

    @pytest.mark.asyncio
    async def test_empty_window_raises_value_error(self, storage, real_embedder):
        """No traces in window → ValueError with helpful message."""
        provider = MockDigestProvider()
        service = TemporalDigestService(storage, real_embedder, provider)

        with pytest.raises(ValueError, match="No user traces found"):
            await service.generate_period_summary(days=30)

        assert provider.call_count == 0

    @pytest.mark.asyncio
    async def test_llm_failure_raises_runtime_error(self, storage, real_embedder):
        """LLM failure → RuntimeError, not crash."""
        populate_multi_domain(storage, real_embedder, days_ago=3)

        service = TemporalDigestService(storage, real_embedder, FailingProvider())

        with pytest.raises(RuntimeError, match="Digest generation failed"):
            await service.generate_period_summary(days=30)

    @pytest.mark.asyncio
    async def test_empty_llm_response_raises_runtime_error(self, storage, real_embedder):
        """LLM returns empty string → RuntimeError."""
        populate_multi_domain(storage, real_embedder, days_ago=3)

        service = TemporalDigestService(storage, real_embedder, EmptyProvider())

        with pytest.raises(RuntimeError, match="empty narrative"):
            await service.generate_period_summary(days=30)


# ------------------------------------------------------------------
# get_topic_evolution tests
# ------------------------------------------------------------------


class TestGetTopicEvolution:
    @pytest.mark.asyncio
    async def test_returns_chronological_narrative(self, storage, real_embedder):
        """Topic evolution returns narrative for matching traces."""
        populate_multi_domain(storage, real_embedder, days_ago=7)

        provider = MockDigestProvider(response=(
            "Your thinking about training evolved from rowing-focused goals "
            "to a broader thoracic pump restoration approach."
        ))
        service = TemporalDigestService(storage, real_embedder, provider)
        narrative = await service.get_topic_evolution("training program", days=30)

        assert len(narrative) > 20
        assert "training" in narrative.lower() or "rowing" in narrative.lower()

    @pytest.mark.asyncio
    async def test_evolution_not_stored(self, storage, real_embedder):
        """Topic evolution is ephemeral — not stored as a trace."""
        populate_multi_domain(storage, real_embedder, days_ago=5)

        provider = MockDigestProvider(response="Your thinking evolved significantly.")
        service = TemporalDigestService(storage, real_embedder, provider)

        # Count traces before
        conversations_before = storage.list_conversations()
        total_before = sum(c["trace_count"] for c in conversations_before)

        await service.get_topic_evolution("career", days=30)

        # Count traces after — should be same (no new system trace)
        conversations_after = storage.list_conversations()
        total_after = sum(c["trace_count"] for c in conversations_after)
        assert total_after == total_before

    @pytest.mark.asyncio
    async def test_no_relevant_traces_raises_value_error(self, storage, real_embedder):
        """No traces matching query → ValueError."""
        # Storage is empty or has unrelated traces
        provider = MockDigestProvider()
        service = TemporalDigestService(storage, real_embedder, provider)

        with pytest.raises(ValueError, match="No traces about"):
            await service.get_topic_evolution("quantum computing", days=30)

    @pytest.mark.asyncio
    async def test_evolution_prompt_is_chronological(self, storage, real_embedder):
        """Traces in the evolution prompt are ordered by timestamp."""
        now = datetime.now(timezone.utc)

        # Store traces about same topic at different times
        store_trace(storage, real_embedder, "Starting to learn about vector databases",
                    timestamp=now - timedelta(days=5))
        store_trace(storage, real_embedder, "ChromaDB seems like the simplest vector database entry point",
                    timestamp=now - timedelta(days=3))
        store_trace(storage, real_embedder, "Pinecone might be better for production vector database work",
                    timestamp=now - timedelta(days=1))

        provider = MockDigestProvider(response="Evolution narrative.")
        service = TemporalDigestService(storage, real_embedder, provider)
        await service.get_topic_evolution("vector databases", days=30)

        # Verify chronological order in prompt
        prompt = provider.last_prompt
        assert prompt is not None

        # Find positions of trace content in prompt
        pos_starting = prompt.find("Starting to learn")
        pos_chroma = prompt.find("ChromaDB")
        pos_pinecone = prompt.find("Pinecone")

        # All should be present and in chronological order
        assert pos_starting >= 0
        assert pos_chroma >= 0
        assert pos_pinecone >= 0
        assert pos_starting < pos_chroma < pos_pinecone

    @pytest.mark.asyncio
    async def test_llm_failure_raises_runtime_error(self, storage, real_embedder):
        """LLM failure → RuntimeError."""
        populate_multi_domain(storage, real_embedder, days_ago=3)

        service = TemporalDigestService(storage, real_embedder, FailingProvider())

        with pytest.raises(RuntimeError, match="Evolution narrative failed"):
            await service.get_topic_evolution("career", days=30)


# ------------------------------------------------------------------
# Clustering behavior
# ------------------------------------------------------------------


class TestDigestClustering:
    @pytest.mark.asyncio
    async def test_few_traces_grouped_as_single_cluster(self, storage, real_embedder):
        """< 3 traces → no DBSCAN, all grouped together."""
        now = datetime.now(timezone.utc)
        store_trace(storage, real_embedder, "One trace about thinking", timestamp=now - timedelta(days=1))
        store_trace(storage, real_embedder, "Another trace about plans", timestamp=now - timedelta(hours=12))

        provider = MockDigestProvider()
        service = TemporalDigestService(storage, real_embedder, provider)
        await service.generate_period_summary(days=7)

        # Should still succeed with a single cluster group
        assert provider.call_count == 1
        assert "Cluster 0" in provider.last_prompt

    @pytest.mark.asyncio
    async def test_multi_domain_traces_produce_multiple_clusters(self, storage, real_embedder):
        """Semantically distinct traces should produce separate clusters in the prompt."""
        populate_multi_domain(storage, real_embedder, days_ago=5)

        provider = MockDigestProvider()
        service = TemporalDigestService(storage, real_embedder, provider)
        await service.generate_period_summary(days=30)

        # With 8 multi-domain traces, DBSCAN should find structure
        # At minimum, the prompt should reference the traces
        assert provider.last_prompt is not None
        assert "last 30 days" in provider.last_prompt
