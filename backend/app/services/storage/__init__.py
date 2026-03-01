"""
Abstract trace storage interface — implementations are swappable (Constraint 3.14).

v2 replaces the proposition-based StorageService with a trace-based interface.
Traces are immutable ground truth. Embeddings are separable (re-embeddable).
Conversations are implicit groupings via conversation_id on traces —
no separate conversations table.

Design: SPEC.md § Data Model
"""

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from .models import Annotation, Connection, Trace, SimilarTrace


class TraceStorageService(ABC):
    """Abstract trace storage interface.

    Three responsibilities:
    1. Trace CRUD (store, get, list by conversation)
    2. Conversation listing (derived from trace groupings)
    3. Embedding storage + vector search (for retrieval pipeline)
    """

    # ------------------------------------------------------------------
    # Trace CRUD
    # ------------------------------------------------------------------

    @abstractmethod
    def store_trace(self, trace: Trace) -> str:
        """Store an immutable trace. Returns its ID.

        Traces are never modified after creation (Constraint 2.11).
        """
        ...

    @abstractmethod
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Retrieve a single trace by ID. Returns None if not found."""
        ...

    @abstractmethod
    def get_traces_by_conversation(self, conversation_id: str) -> list[Trace]:
        """Get all traces in a conversation, ordered by timestamp ascending."""
        ...

    # ------------------------------------------------------------------
    # Conversation listing (derived from traces)
    # ------------------------------------------------------------------

    @abstractmethod
    def list_conversations(self) -> list[dict]:
        """List all conversations derived from trace groupings.

        Returns list of dicts with:
            id: str              — conversation_id
            first_trace_at: str  — timestamp of earliest trace
            last_trace_at: str   — timestamp of latest trace
            trace_count: int     — number of traces in conversation

        Ordered by last_trace_at descending (most recent first).
        """
        ...

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------

    @abstractmethod
    def store_annotation(self, annotation: Annotation) -> str:
        """Store a computed annotation on a trace. Returns its ID."""
        ...

    @abstractmethod
    def get_annotations_for_trace(self, trace_id: str) -> list[Annotation]:
        """Get all annotations for a trace, ordered by extracted_at."""
        ...

    @abstractmethod
    def get_annotations_by_type(self, annotation_type: str) -> list[Annotation]:
        """Get all annotations of a given type across all traces."""
        ...

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------

    @abstractmethod
    def store_connection(self, connection: Connection) -> None:
        """Store a connection between two traces.

        Uses INSERT OR REPLACE — re-computing semantic connections
        overwrites previous values for the same (source, target, type).
        """
        ...

    @abstractmethod
    def get_connections_for_trace(self, trace_id: str) -> list[Connection]:
        """Get all connections where trace_id is source OR target."""
        ...

    @abstractmethod
    def get_connections_by_type(self, connection_type: str) -> list[Connection]:
        """Get all connections of a given type."""
        ...

    @abstractmethod
    def delete_connections_by_type(self, connection_type: str) -> int:
        """Delete all connections of a given type. Returns count deleted.

        Used when recomputing semantic connections — clear old, insert new.
        """
        ...

    # ------------------------------------------------------------------
    # Embeddings + vector search
    # ------------------------------------------------------------------

    @abstractmethod
    def store_embedding(self, trace_id: str, embedding: np.ndarray, model: str) -> None:
        """Store an embedding vector for a trace.

        Overwrites any existing embedding for this trace_id
        (supports re-embedding with better models).
        """
        ...

    @abstractmethod
    def find_similar(
        self,
        embedding: np.ndarray,
        threshold: float = 0.35,
        limit: int = 10,
    ) -> list[SimilarTrace]:
        """Find traces with cosine similarity above threshold.

        Returns results sorted by similarity descending, capped at limit.
        """
        ...

    @abstractmethod
    def get_all_embeddings(self) -> tuple[list[str], np.ndarray]:
        """Load all embeddings into memory.

        Returns (trace_ids, embedding_matrix) where matrix is (N, dims).
        Returns ([], empty_array) if no embeddings exist.
        Used by projection service (UMAP) and for cache rebuilding.
        """
        ...
