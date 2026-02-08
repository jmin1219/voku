"""
Embedding service for semantic similarity within Kuzu graph.
Uses bge-base-en-v1.5 for 768-dim vectors. Provides methods for embedding text and calculating cosine similarity.
"""

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Converts text to semantic embeddings (768-dim vectors)."""

    def __init__(self):
        # Load model once, cache it for reuse
        self.model = SentenceTransformer("BAAI/bge-base-en-v1.5")

    def embed(self, text: str) -> list[float]:
        """
        Generate a 768-dim embedding for the given text.

        Args:
            text: Input string to embed

        Returns:
            List of 768 floats representing the semantic embedding
        """
        # model.encode() returns a numpy array; convert to list for easier storage
        return self.model.encode(text).tolist()


# Quick check to verify embedding generation works
if __name__ == "__main__":
    service = EmbeddingService()
    sample_text = "The cat sat on the mat."
    embedding = service.embed(sample_text)
    print(f"Embedding for '{sample_text}':")
    print(embedding)
