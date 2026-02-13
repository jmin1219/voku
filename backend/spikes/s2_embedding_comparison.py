"""
Spike S2: EmbeddingGemma vs bge-base-en-v1.5 comparison on Voku's actual data.

Question: Is EmbeddingGemma measurably better than bge-base on personal belief propositions?
Method: Embed 20 propositions with both models, run 10 queries, compare retrieval quality.
Decision: Clear winner becomes default for Component 1.3.
"""

import time
import numpy as np
import requests
from sentence_transformers import SentenceTransformer

# --- Test Data ---
# 20 real-ish propositions extracted from Jaymin's conversations
PROPOSITIONS = [
    "I think my main limiter for rowing is my ankle — I can't get full extension.",
    "My morning formula is shower then smoothie then first task decided the night before.",
    "I left athletic training for CS partly because of prestige concerns.",
    "The interest-based nervous system means I need structure over expectations.",
    "I believe Voku should be a cognitive mirror, not an advisor.",
    "My current 2K row time is 8:05.",
    "I'm pursuing AI engineering co-op positions for early 2027 start.",
    "I think React is the best frontend framework for Voku's visualization.",
    "Sleep issues might fix themselves if I just go to bed when tired.",
    "The internal monitor is hypervigilant self-evaluation from 9 schools K-12.",
    "I think temporal accuracy is Voku's core differentiator, not just memory.",
    "My father is CEO of a Korean investment bank.",
    "I find that oral breathing engages my legs properly during rowing.",
    "Claude's task duration distortion means my brain inflates time estimates by 3x.",
    "I'm currently underfueling — skipping breakfast contributes to energy collapse.",
    "The afternoon murk question is: am I tired or am I lonely?",
    "I think the knowledge graph market will grow to $28.5B by 2028.",
    "My training anchor is 5-6pm daily with 100% success rate.",
    "I believe nobody quantifies your mind — that's the gap Voku fills.",
    "I moved training to 3pm today and it worked — the evening opened up.",
]

# 10 test queries with expected top-3 proposition indices
QUERIES = [
    ("What limits my rowing performance?", [0, 12]),
    ("How do I start my mornings?", [1, 14]),
    ("Why did I switch from athletic training to CS?", [2, 3]),
    ("What is Voku's core value proposition?", [4, 10, 18]),
    ("What are my career plans?", [6]),
    ("How do I handle energy crashes in the afternoon?", [14, 15, 19]),
    ("What's my relationship with my father?", [11]),
    ("How does my brain distort task difficulty?", [13, 3]),
    ("What time do I train?", [17, 19]),
    ("What's the market opportunity for knowledge graphs?", [16, 18]),
]


def embed_bge(texts: list[str]) -> np.ndarray:
    """Embed with bge-base-en-v1.5 via sentence-transformers."""
    model = SentenceTransformer("BAAI/bge-base-en-v1.5")
    return model.encode(texts, normalize_embeddings=True)


def embed_gemma(texts: list[str]) -> np.ndarray:
    """Embed with EmbeddingGemma via Ollama API."""
    embeddings = []
    for text in texts:
        resp = requests.post(
            "http://localhost:11434/api/embed",
            json={"model": "embeddinggemma", "input": text},
        )
        resp.raise_for_status()
        embeddings.append(resp.json()["embeddings"][0])
    return np.array(embeddings, dtype=np.float32)


def cosine_search(query_emb: np.ndarray, corpus_emb: np.ndarray, top_k: int = 5):
    """Return indices of top-k most similar embeddings."""
    query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-10)
    corpus_norm = corpus_emb / (np.linalg.norm(corpus_emb, axis=1, keepdims=True) + 1e-10)
    scores = corpus_norm @ query_norm
    top_indices = np.argsort(scores)[::-1][:top_k]
    return top_indices, scores[top_indices]


def evaluate_model(name: str, embed_fn, propositions: list[str], queries: list):
    """Run all queries against embedded propositions, score retrieval quality."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

    # Embed propositions
    t0 = time.time()
    prop_embeddings = embed_fn(propositions)
    embed_time = time.time() - t0
    print(f"Embedded {len(propositions)} propositions in {embed_time:.2f}s")
    print(f"Embedding shape: {prop_embeddings.shape}")

    # Run queries
    total_hits = 0
    total_expected = 0

    for query_text, expected_indices in queries:
        query_emb = embed_fn([query_text])[0]
        top_indices, top_scores = cosine_search(query_emb, prop_embeddings, top_k=5)

        # How many expected propositions appear in top-5?
        hits = set(top_indices) & set(expected_indices)
        total_hits += len(hits)
        total_expected += len(expected_indices)

        hit_marker = "✓" if len(hits) == len(expected_indices) else "○" if hits else "✗"
        print(f"\n{hit_marker} Query: {query_text}")
        print(f"  Expected: {expected_indices}")
        print(f"  Got top-5: {list(top_indices)} (scores: {[f'{s:.3f}' for s in top_scores]})")
        for idx in top_indices[:3]:
            marker = " ← HIT" if idx in expected_indices else ""
            print(f"    [{idx}] {propositions[idx][:70]}...{marker}")

    recall = total_hits / total_expected if total_expected > 0 else 0
    print(f"\n--- SUMMARY ---")
    print(f"Recall@5: {total_hits}/{total_expected} = {recall:.1%}")
    print(f"Embed time: {embed_time:.2f}s for {len(propositions)} texts")
    return recall, embed_time


if __name__ == "__main__":
    print("Spike S2: Embedding Model Comparison")
    print("=" * 60)

    r1, t1 = evaluate_model("bge-base-en-v1.5 (sentence-transformers)", embed_bge, PROPOSITIONS, QUERIES)
    r2, t2 = evaluate_model("EmbeddingGemma (Ollama)", embed_gemma, PROPOSITIONS, QUERIES)

    print(f"\n{'='*60}")
    print(f"  DECISION")
    print(f"{'='*60}")
    print(f"bge-base:       Recall@5 = {r1:.1%}, Embed time = {t1:.2f}s")
    print(f"EmbeddingGemma: Recall@5 = {r2:.1%}, Embed time = {t2:.2f}s")

    if r2 > r1 + 0.05:
        print("\n→ EmbeddingGemma wins. Switch to Ollama embeddings.")
    elif r1 > r2 + 0.05:
        print("\n→ bge-base wins. Stay with sentence-transformers (simpler).")
    else:
        print("\n→ No meaningful difference. Stay with bge-base (simpler).")
