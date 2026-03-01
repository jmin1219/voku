"""
Connection computation service — builds the graph topology.

Computes two connection types from existing traces:
  - Temporal: sequential traces within a session (auto-generated)
  - Semantic: k-NN from embedding cosine similarity (ambient topology)

Intentional and supersession connections are user/annotation-driven
and handled elsewhere.

Design: SPEC.md § Data Model, Layer 3
"""

from datetime import datetime, timezone

import numpy as np

from app.services.storage import TraceStorageService
from app.services.storage.models import Connection


class ConnectionService:
    """Compute and store connections between traces."""

    def __init__(self, storage: TraceStorageService):
        self._storage = storage

    def compute_temporal_connections(self) -> int:
        """Generate temporal connections from parent_trace_id links.

        For each trace with a parent, creates a temporal connection:
        parent → child with weight 1.0.

        Clears existing temporal connections first (idempotent recomputation).
        Returns the number of connections created.
        """
        self._storage.delete_connections_by_type("temporal")
        now = datetime.now(timezone.utc).isoformat()

        # Get all conversations, then walk each chain
        conversations = self._storage.list_conversations()
        count = 0

        for conv in conversations:
            traces = self._storage.get_traces_by_conversation(conv["id"])
            for trace in traces:
                if trace.parent_trace_id is not None:
                    conn = Connection(
                        source_id=trace.parent_trace_id,
                        target_id=trace.id,
                        type="temporal",
                        weight=1.0,
                        created_at=now,
                    )
                    self._storage.store_connection(conn)
                    count += 1

        return count

    def compute_semantic_connections(self, k: int = 5, threshold: float = 0.3) -> int:
        """Generate k-NN semantic connections from embedding similarity.

        For each trace, connects to its k nearest neighbors (by cosine
        similarity in embedding space) if similarity exceeds threshold.

        Clears existing semantic connections first (idempotent recomputation).
        Returns the number of connections created.

        At 1000 traces × k=5: ~5000 connections. At 10K: ~50K.
        Computation: O(n²) cosine similarity matrix, fast via numpy.
        """
        self._storage.delete_connections_by_type("semantic")
        now = datetime.now(timezone.utc).isoformat()

        ids, matrix = self._storage.get_all_embeddings()
        if len(ids) < 2:
            return 0

        # Compute full cosine similarity matrix
        norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
        normalized = matrix / norms
        sim_matrix = normalized @ normalized.T

        # Zero out self-similarity
        np.fill_diagonal(sim_matrix, 0.0)

        count = 0
        for i in range(len(ids)):
            scores = sim_matrix[i]

            # Get top-k indices above threshold
            above_threshold = np.where(scores >= threshold)[0]
            if len(above_threshold) == 0:
                continue

            # Sort by similarity descending, take top k
            sorted_indices = above_threshold[np.argsort(scores[above_threshold])[::-1]]
            top_k = sorted_indices[:k]

            for j in top_k:
                if int(j) == i:
                    continue  # Skip self-connections

                # Deduplicate: only store if source_id < target_id (lexicographic)
                # to avoid A→B and B→A both existing
                a, b = ids[i], ids[int(j)]
                if a < b:
                    src, tgt = a, b
                else:
                    src, tgt = b, a

                conn = Connection(
                    source_id=src,
                    target_id=tgt,
                    type="semantic",
                    weight=float(scores[j]),
                    created_at=now,
                )
                self._storage.store_connection(conn)
                count += 1

        return count

    def compute_all(self, k: int = 5, threshold: float = 0.3) -> dict:
        """Compute all connection types. Returns counts per type."""
        temporal = self.compute_temporal_connections()
        semantic = self.compute_semantic_connections(k=k, threshold=threshold)
        return {"temporal": temporal, "semantic": semantic}
