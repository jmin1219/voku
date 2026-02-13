"""
Abstract embedding interface — implementations are swappable (Constraint 3.13).

Component 1.3 in COMPONENT_SPEC.md.
Spike S2 decision: bge-base-en-v1.5 is default (95% Recall@5, no Ollama dependency).
"""

from abc import ABC, abstractmethod
import numpy as np


class EmbeddingProvider(ABC):
    """Abstract embedding interface."""

    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Embed a single text into a vector."""
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed multiple texts. Returns (N, dimensions) matrix."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Dimensionality of output vectors."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier for provenance tracking."""
        ...
