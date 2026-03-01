"""
Trace retrieval — query traces with temporal-weighted ranking.

v2 replacement for RetrievalService. Simplified: no proposition types,
no status filtering, no topic timeline. Just traces ranked by a blend
of embedding similarity and recency.

Pipeline: query → embed → find_similar → weight by recency → rank → return

Design: SPEC.md § Context Assembly
Constraint 0.1: Conversation quality must improve with accumulated context.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from app.services.storage import TraceStorageService
from app.services.storage.models import Trace
from app.services.embedding.bge import BGEBaseEmbedding


@dataclass
class TraceRetrievalResult:
    """A trace returned from retrieval with its scoring breakdown.

    Consumers (ContextAssembly, frontend) use the combined score for
    ranking and the individual scores for display/debugging.
    """

    trace: Trace
    similarity: float       # Cosine similarity [0, 1]
    recency: float          # Exponential decay [0, 1]
    combined: float         # Blended score


class TraceRetrievalService:
    """Retrieve relevant traces for a query, weighted by similarity and recency.

    The temporal_weight parameter controls the blend:
      0.0 = pure similarity (flat retrieval)
      0.3 = recommended blend (default)
      1.0 = pure recency (not useful — ignores relevance)
    """

    def __init__(self, storage: TraceStorageService, embedder: BGEBaseEmbedding):
        self._storage = storage
        self._embedder = embedder

    # Connection types to follow during graph expansion.
    # Semantic is excluded — redundant with vector search.
    EXPAND_CONNECTION_TYPES = {"temporal", "intentional"}
    GRAPH_DISCOUNT = 0.7  # Expanded traces score at 70% of parent

    # Annotation types that receive an intention boost in retrieval
    INTENTION_TYPES = {"intention", "commitment"}

    def retrieve(
        self,
        query: str,
        limit: int = 10,
        temporal_weight: float = 0.3,
        similarity_threshold: float = 0.35,
        use_graph: bool = True,
        intention_boost: float = 1.3,
    ) -> list[TraceRetrievalResult]:
        """Retrieve traces relevant to a query.

        Args:
            query: Natural language query string.
            limit: Maximum results to return.
            temporal_weight: Blend factor. 0.0 = pure similarity,
                           0.3 = recommended, 1.0 = pure recency.
            similarity_threshold: Minimum cosine similarity to include.
            use_graph: If True, expand results via temporal/intentional
                      connections (1-hop). Default True.
            intention_boost: Multiplier for traces with intention/commitment
                           annotations. Default 1.3.

        Returns:
            List of TraceRetrievalResult sorted by combined score descending.
        """
        # 1. Embed the query
        query_embedding = self._embedder.embed(query)

        # 2. Get similar traces above threshold (over-fetch for re-ranking)
        similar = self._storage.find_similar(
            query_embedding,
            threshold=similarity_threshold,
            limit=limit * 3,
        )

        if not similar:
            return []

        # 3. Compute recency and blend scores
        now = datetime.now(timezone.utc)
        results_by_id: dict[str, TraceRetrievalResult] = {}
        for match in similar:
            trace = match.trace
            similarity = match.score
            recency = compute_recency(trace.timestamp, now)
            combined = (
                similarity * (1.0 - temporal_weight)
                + recency * temporal_weight
            )
            results_by_id[trace.id] = TraceRetrievalResult(
                trace=trace,
                similarity=similarity,
                recency=recency,
                combined=combined,
            )

        # 4. Intention boost: elevate traces with intention/commitment annotations
        if intention_boost > 1.0:
            self._apply_intention_boost(results_by_id, intention_boost)

        # 5. Graph expansion: 1-hop via temporal/intentional connections
        if use_graph:
            self._expand_via_connections(results_by_id, now, temporal_weight, limit)

        # 6. Sort by combined score, return top limit
        results = sorted(results_by_id.values(), key=lambda r: r.combined, reverse=True)
        return results[:limit]

    def _apply_intention_boost(
        self,
        results_by_id: dict[str, "TraceRetrievalResult"],
        boost: float,
    ) -> None:
        """Boost scores for traces with intention/commitment annotations.

        Queries storage for annotations on each result trace. If any
        annotation has a type in INTENTION_TYPES, multiply the combined
        score by the boost factor. Mutates results_by_id in place.
        """
        for trace_id, result in results_by_id.items():
            annotations = self._storage.get_annotations_for_trace(trace_id)
            has_intention = any(
                ann.type in self.INTENTION_TYPES for ann in annotations
            )
            if has_intention:
                result.combined *= boost

    def _expand_via_connections(
        self,
        results_by_id: dict[str, "TraceRetrievalResult"],
        now: datetime,
        temporal_weight: float,
        limit: int,
    ) -> None:
        """Expand results by following temporal/intentional connections.

        For each vector-matched trace, fetch its connections and add
        connected traces as candidates with a discounted score.
        Mutates results_by_id in place. Bounded to 2× limit.
        """
        max_total = limit * 2
        # Snapshot the current IDs to iterate (don't mutate while iterating)
        seed_ids = list(results_by_id.keys())

        for trace_id in seed_ids:
            if len(results_by_id) >= max_total:
                break

            parent_result = results_by_id[trace_id]
            connections = self._storage.get_connections_for_trace(trace_id)

            for conn in connections:
                if conn.type not in self.EXPAND_CONNECTION_TYPES:
                    continue
                if len(results_by_id) >= max_total:
                    break

                # Find the neighbor ID (could be source or target)
                neighbor_id = (
                    conn.target_id if conn.source_id == trace_id
                    else conn.source_id
                )

                # Already in results — keep whichever score is higher
                if neighbor_id in results_by_id:
                    continue

                # Fetch the neighbor trace
                neighbor = self._storage.get_trace(neighbor_id)
                if neighbor is None:
                    continue

                # Discounted score from parent
                conn_weight = conn.weight if conn.weight else 1.0
                discounted = parent_result.combined * conn_weight * self.GRAPH_DISCOUNT
                recency = compute_recency(neighbor.timestamp, now)

                results_by_id[neighbor_id] = TraceRetrievalResult(
                    trace=neighbor,
                    similarity=0.0,  # Not from vector search
                    recency=recency,
                    combined=discounted,
                )


def compute_recency(
    timestamp: str,
    now: datetime,
    half_life_days: float = 30.0,
) -> float:
    """Compute recency score with exponential decay.

    Returns 1.0 for now, 0.5 at half_life_days ago, approaching 0 for old.
    Exposed as module-level function for direct testing.
    """
    try:
        created = datetime.fromisoformat(timestamp)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.5  # Default for unparseable timestamps

    age_days = (now - created).total_seconds() / 86400.0
    if age_days < 0:
        return 1.0  # Future timestamp (shouldn't happen)

    # Exponential decay: score = 2^(-age/half_life)
    return float(2.0 ** (-age_days / half_life_days))
