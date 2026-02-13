"""
Abstract storage interface — implementations are swappable (Constraint 3.13).

Component 1.2 in COMPONENT_SPEC.md.
"""

from abc import ABC, abstractmethod
from datetime import datetime

import numpy as np

from .models import StoredProposition, SimilarResult


class StorageService(ABC):
    """Abstract storage interface."""

    @abstractmethod
    def store_proposition(self, proposition: StoredProposition) -> str:
        """Store a proposition. Returns its ID."""
        ...

    @abstractmethod
    def store_embedding(self, proposition_id: str, embedding: np.ndarray, model: str) -> None:
        """Store an embedding vector for a proposition."""
        ...

    @abstractmethod
    def find_similar(self, embedding: np.ndarray, threshold: float = 0.85, limit: int = 10) -> list[SimilarResult]:
        """Find propositions with similar embeddings above threshold."""
        ...

    @abstractmethod
    def find_by_timerange(self, start: datetime, end: datetime) -> list[StoredProposition]:
        """Find propositions created within a time range."""
        ...

    @abstractmethod
    def find_by_session(self, session_id: str) -> list[StoredProposition]:
        """Find all propositions from a specific conversation session."""
        ...

    @abstractmethod
    def get_all_embeddings(self) -> tuple[list[str], np.ndarray]:
        """Load all embeddings into memory. Returns (ids, embedding_matrix)."""
        ...
