"""Tests for k-NN edge computation in ProjectionService.

Validates _compute_knn_edges independently from the full projection pipeline.
Covers: deduplication, weight correctness, k-capping, edge cases.
"""

import numpy as np
import pytest

from services.projection import _compute_knn_edges


# --- Fixtures ---

def _random_embeddings(n: int, dim: int = 768, seed: int = 42) -> np.ndarray:
    """Reproducible random embeddings."""
    rng = np.random.RandomState(seed)
    X = rng.randn(n, dim).astype(np.float32)
    return X


def _ids(n: int) -> list[str]:
    return [f"prop_{i:03d}" for i in range(n)]


# --- Core behavior ---

class TestKNNEdgeComputation:

    def test_basic_output_structure(self):
        """Each edge has source, target, weight — all present and typed."""
        X = _random_embeddings(10)
        edges = _compute_knn_edges(X, _ids(10), k=3)
        assert len(edges) > 0
        for e in edges:
            assert "source" in e
            assert "target" in e
            assert "weight" in e
            assert isinstance(e["source"], str)
            assert isinstance(e["target"], str)
            assert isinstance(e["weight"], float)

    def test_weights_are_positive(self):
        """All returned edges have positive cosine similarity."""
        X = _random_embeddings(20)
        edges = _compute_knn_edges(X, _ids(20), k=5)
        for e in edges:
            assert e["weight"] > 0, f"Non-positive weight: {e['weight']}"

    def test_weights_bounded_zero_to_one(self):
        """Cosine similarity of normalized vectors stays in [0, 1] for typical data."""
        X = _random_embeddings(50)
        edges = _compute_knn_edges(X, _ids(50), k=5)
        for e in edges:
            assert 0 < e["weight"] <= 1.0, f"Weight out of range: {e['weight']}"

    def test_no_self_edges(self):
        """No edge should connect a node to itself."""
        X = _random_embeddings(15)
        edges = _compute_knn_edges(X, _ids(15), k=5)
        for e in edges:
            assert e["source"] != e["target"], f"Self-edge: {e['source']}"

    def test_deduplication(self):
        """Each undirected pair appears at most once."""
        X = _random_embeddings(30)
        edges = _compute_knn_edges(X, _ids(30), k=5)
        pairs = set()
        for e in edges:
            pair = frozenset((e["source"], e["target"]))
            assert pair not in pairs, f"Duplicate edge: {e['source']} <-> {e['target']}"
            pairs.add(pair)

    def test_edge_count_upper_bound(self):
        """With n nodes and k neighbors, max edges = n*k/2 (undirected, deduplicated).
        In practice often less due to reciprocal neighbors."""
        n, k = 20, 5
        X = _random_embeddings(n)
        edges = _compute_knn_edges(X, _ids(n), k=k)
        # Upper bound: each of n nodes contributes k edges, /2 for dedup
        assert len(edges) <= n * k  # loose bound (before dedup removes ~half)
        assert len(edges) > 0

    def test_known_similarity_ordering(self):
        """Hand-crafted vectors: identical vectors should connect with weight ~1.0."""
        # 3 vectors: A and B identical, C orthogonal
        dim = 10
        a = np.ones(dim, dtype=np.float32)
        b = np.ones(dim, dtype=np.float32)  # identical to a
        c = np.zeros(dim, dtype=np.float32)
        c[0] = 1.0  # orthogonal-ish to a/b

        X = np.array([a, b, c])
        ids = ["identical_a", "identical_b", "different_c"]
        edges = _compute_knn_edges(X, ids, k=2)

        # Find the edge between identical_a and identical_b
        ab_edge = [e for e in edges
                    if set([e["source"], e["target"]]) == {"identical_a", "identical_b"}]
        assert len(ab_edge) == 1, "Missing edge between identical vectors"
        assert ab_edge[0]["weight"] == pytest.approx(1.0, abs=0.001)

    def test_ids_match_input(self):
        """All source/target IDs come from the input ID list."""
        ids = _ids(15)
        X = _random_embeddings(15)
        edges = _compute_knn_edges(X, ids, k=3)
        id_set = set(ids)
        for e in edges:
            assert e["source"] in id_set
            assert e["target"] in id_set


# --- Edge cases ---

class TestKNNEdgeCases:

    def test_single_node(self):
        """One node = no edges possible."""
        X = _random_embeddings(1)
        edges = _compute_knn_edges(X, _ids(1), k=5)
        assert edges == []

    def test_two_nodes(self):
        """Two nodes = exactly one edge (regardless of k)."""
        X = _random_embeddings(2)
        edges = _compute_knn_edges(X, _ids(2), k=5)
        assert len(edges) == 1

    def test_k_exceeds_n(self):
        """k > n-1 should gracefully cap to n-1 neighbors."""
        X = _random_embeddings(5)
        edges = _compute_knn_edges(X, _ids(5), k=100)
        # Should not crash, should return valid edges
        assert len(edges) > 0
        for e in edges:
            assert e["source"] != e["target"]

    def test_zero_vector_handling(self):
        """Zero-norm vectors should not cause NaN/Inf — guarded by norm clamping."""
        X = _random_embeddings(5)
        X[2] = 0.0  # inject a zero vector
        edges = _compute_knn_edges(X, _ids(5), k=3)
        for e in edges:
            assert np.isfinite(e["weight"]), f"Non-finite weight: {e['weight']}"

    def test_empty_input(self):
        """Empty array = no edges."""
        X = np.array([]).reshape(0, 768)
        edges = _compute_knn_edges(X, [], k=5)
        assert edges == []

    def test_k_equals_one(self):
        """k=1: each node connects to its single nearest neighbor."""
        n = 10
        X = _random_embeddings(n)
        edges = _compute_knn_edges(X, _ids(n), k=1)
        # With k=1, max possible edges = n (before dedup), after dedup ≤ n
        assert 1 <= len(edges) <= n

    def test_weight_precision(self):
        """Weights should be rounded to 4 decimal places."""
        X = _random_embeddings(10)
        edges = _compute_knn_edges(X, _ids(10), k=3)
        for e in edges:
            weight_str = f"{e['weight']:.4f}"
            assert float(weight_str) == e["weight"]
