"""
BGE-base-en-v1.5 embedding implementation via sentence-transformers.

Runs entirely on CPU, no external service dependency.
768 dimensions, ~420MB model download on first use.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from . import EmbeddingProvider


class BGEBaseEmbedding(EmbeddingProvider):
    """sentence-transformers bge-base-en-v1.5, 768 dims."""

    def __init__(self):
        self._model = SentenceTransformer("BAAI/bge-base-en-v1.5")

    def embed(self, text: str) -> np.ndarray:
        """Embed a single text. Returns (768,) float32 array."""
        return self._model.encode(text, normalize_embeddings=True)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed multiple texts. Returns (N, 768) float32 matrix."""
        return self._model.encode(texts, normalize_embeddings=True)

    @property
    def dimensions(self) -> int:
        return 768

    @property
    def model_name(self) -> str:
        return "bge-base-en-v1.5"
