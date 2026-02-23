"""
Retrieval service — query propositions with temporal awareness.

Component 2.2 in COMPONENT_SPEC.md.

Two modes:
- Flat: Pure embedding similarity (temporal_weight=0)
- Temporal: Weighted blend of similarity + recency (temporal_weight>0)

This is the component that Phase 2 evaluates: does temporal weighting
improve retrieval quality over flat embedding search?
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from app.services.storage.sqlite_storage import SQLiteStorage
from app.services.storage.models import StoredProposition
from app.services.embedding.bge import BGEBaseEmbedding


@dataclass
class RetrievalResult:
    """A single retrieval result with scoring breakdown."""
    proposition_id: str
    text: str
    node_type: str
    similarity: float          # Embedding cosine similarity [0, 1]
    recency_score: float       # Temporal weighting [0, 1]
    combined_score: float      # Blended score
    confidence: float          # Extraction confidence
    created_at: str
    status: str                # active / superseded / contradicted
    source_file: Optional[str] = None
    superseded_in_conversation: bool = False


@dataclass
class TopicTimeline:
    """Chronological view of beliefs on a topic."""
    current_belief: Optional[RetrievalResult]   # Most recent ACTIVE
    history: list[RetrievalResult]               # All results, chronological
    superseded: list[RetrievalResult]            # Explicitly superseded


class RetrievalService:
    """Retrieve relevant context for a query.

    Supports flat (pure similarity) and temporal (similarity + recency)
    retrieval modes via the temporal_weight parameter.
    """

    def __init__(self, storage: SQLiteStorage, embedder: BGEBaseEmbedding):
        self.storage = storage
        self.embedder = embedder

    def retrieve(
        self,
        query: str,
        limit: int = 10,
        temporal_weight: float = 0.0,
        similarity_threshold: float = 0.3,
    ) -> list[RetrievalResult]:
        """Retrieve propositions relevant to a query.

        Args:
            query: Natural language query string.
            limit: Maximum results to return.
            temporal_weight: 0.0 = pure similarity (flat mode),
                           0.3 = recommended temporal blend,
                           1.0 = pure recency (not useful).
            similarity_threshold: Minimum cosine similarity to include.

        Returns:
            List of RetrievalResult sorted by combined_score descending.
        """
        # 1. Embed the query
        query_embedding = self.embedder.embed(query)

        # 2. Get all similar propositions above threshold
        similar = self.storage.find_similar(
            query_embedding,
            threshold=similarity_threshold,
            limit=limit * 3,  # Over-fetch to allow re-ranking
        )

        if not similar:
            return []

        # 3. Compute recency scores
        now = datetime.now(timezone.utc)
        results = []
        for sr in similar:
            prop = sr.proposition
            similarity = sr.score

            # Recency: exponential decay, half-life of 30 days
            recency = self._compute_recency(prop.created_at, now)

            # Combined score
            combined = (
                similarity * (1.0 - temporal_weight)
                + recency * temporal_weight
            )

            results.append(RetrievalResult(
                proposition_id=prop.id,
                text=prop.text,
                node_type=prop.node_type,
                similarity=similarity,
                recency_score=recency,
                combined_score=combined,
                confidence=prop.confidence,
                created_at=prop.created_at,
                status=prop.status,
                source_file=prop.source_file,
                superseded_in_conversation=prop.superseded_in_conversation,
            ))

        # 4. Sort by combined score, return top N
        results.sort(key=lambda r: r.combined_score, reverse=True)
        return results[:limit]

    def retrieve_for_topic(
        self,
        topic: str,
        include_history: bool = True,
        similarity_threshold: float = 0.4,
    ) -> TopicTimeline:
        """Retrieve the belief timeline for a topic.

        Returns the current active belief and optionally the full
        evolution history (superseded positions).
        """
        # Get all relevant propositions (high over-fetch for completeness)
        all_results = self.retrieve(
            query=topic,
            limit=50,
            temporal_weight=0.0,  # Pure similarity for topic matching
            similarity_threshold=similarity_threshold,
        )

        if not all_results:
            return TopicTimeline(
                current_belief=None,
                history=[],
                superseded=[],
            )

        # Sort chronologically for timeline
        chronological = sorted(all_results, key=lambda r: r.created_at)

        # Separate active vs superseded
        active = [r for r in chronological if r.status == "active" and not r.superseded_in_conversation]
        superseded = [r for r in chronological if r.status == "superseded" or r.superseded_in_conversation]

        # Current belief = most recent active proposition
        current = active[-1] if active else None

        return TopicTimeline(
            current_belief=current,
            history=chronological if include_history else [],
            superseded=superseded,
        )

    @staticmethod
    def _compute_recency(created_at: str, now: datetime, half_life_days: float = 30.0) -> float:
        """Compute recency score with exponential decay.

        Returns 1.0 for now, 0.5 at half_life_days ago, approaching 0 for old.
        """
        try:
            created = datetime.fromisoformat(created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return 0.5  # Default for unparseable dates

        age_days = (now - created).total_seconds() / 86400.0
        if age_days < 0:
            return 1.0  # Future date (shouldn't happen)

        # Exponential decay: score = 2^(-age/half_life)
        decay = 2.0 ** (-age_days / half_life_days)
        return float(decay)
