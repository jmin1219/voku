"""
Golden set evaluation — first ablation: temporal vs flat retrieval.

Runs all golden queries against m2_conversation.db in both modes
and compares retrieval quality.

Usage:
    cd backend && python -m tests.golden.run_ablation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))

from services.retrieval import RetrievalService
from services.storage.sqlite_storage import SQLiteStorage
from services.embedding.bge import BGEBaseEmbedding
from tests.golden.golden_queries import GOLDEN_SET


DB_PATH = Path(__file__).parent.parent.parent / "data" / "m2_conversation.db"


def evaluate_query(retrieval: RetrievalService, query_spec: dict, temporal_weight: float) -> dict:
    """Run one golden query and check expected/excluded texts."""
    q = query_spec
    results = retrieval.retrieve(
        q["query"],
        limit=q["k"],
        temporal_weight=temporal_weight,
        similarity_threshold=0.3,
    )

    texts = [r.text for r in results]
    texts_lower = [t.lower() for t in texts]

    # Check expected
    hits = []
    misses = []
    for expected in q["expected_texts"]:
        found = any(expected.lower() in t for t in texts_lower)
        if found:
            hits.append(expected)
        else:
            misses.append(expected)

    # Check excluded
    noise = []
    for excluded in q.get("excluded_texts", []):
        found = any(excluded.lower() in t for t in texts_lower)
        if found:
            noise.append(excluded)

    passed = len(misses) == 0 and len(noise) == 0
    precision = len(hits) / len(q["expected_texts"]) if q["expected_texts"] else 1.0

    return {
        "id": q["id"],
        "query": q["query"],
        "passed": passed,
        "precision": precision,
        "hits": hits,
        "misses": misses,
        "noise": noise,
        "top_results": [(r.text[:70], f"{r.combined_score:.3f}", f"sim={r.similarity:.3f}", f"rec={r.recency_score:.3f}") for r in results[:5]],
    }


def run_ablation():
    storage = SQLiteStorage(DB_PATH)
    embedder = BGEBaseEmbedding()
    retrieval = RetrievalService(storage, embedder)

    modes = [
        ("FLAT (temporal_weight=0.0)", 0.0),
        ("TEMPORAL (temporal_weight=0.3)", 0.3),
    ]

    for mode_name, tw in modes:
        print(f"\n{'=' * 70}")
        print(f"  {mode_name}")
        print(f"{'=' * 70}")

        total = 0
        passed = 0
        total_precision = 0.0

        for spec in GOLDEN_SET:
            result = evaluate_query(retrieval, spec, tw)
            total += 1
            if result["passed"]:
                passed += 1
            total_precision += result["precision"]

            status = "✅" if result["passed"] else "❌"
            print(f"\n  {status} {result['id']} — {result['query']}")
            if result["misses"]:
                print(f"     MISSING: {result['misses']}")
            if result["noise"]:
                print(f"     NOISE:   {result['noise']}")
            for i, (text, combined, sim, rec) in enumerate(result["top_results"][:3]):
                print(f"     [{i+1}] {combined} ({sim}, {rec}) {text}")

        avg_precision = total_precision / total if total else 0
        print(f"\n  {'─' * 60}")
        print(f"  PASS: {passed}/{total} ({passed/total*100:.0f}%)   Avg Precision: {avg_precision:.2f}")

    # --- Topic Timeline test ---
    print(f"\n{'=' * 70}")
    print(f"  TOPIC TIMELINE — 'database choice'")
    print(f"{'=' * 70}")
    timeline = retrieval.retrieve_for_topic("database choice")
    if timeline.current_belief:
        print(f"  Current: {timeline.current_belief.text[:80]}")
        print(f"           (created: {timeline.current_belief.created_at[:10]}, sim={timeline.current_belief.similarity:.3f})")
    print(f"  History: {len(timeline.history)} items")
    for h in timeline.history:
        flag = " ⚡superseded" if h.superseded_in_conversation else ""
        print(f"    {h.created_at[:10]} [{h.node_type:9s}] {h.text[:65]}{flag}")
    print(f"  Superseded: {len(timeline.superseded)} items")

    print(f"\n{'=' * 70}")
    print(f"  TOPIC TIMELINE — 'breathing exercise training'")
    print(f"{'=' * 70}")
    timeline = retrieval.retrieve_for_topic("breathing technique for exercise")
    if timeline.current_belief:
        print(f"  Current: {timeline.current_belief.text[:80]}")
        print(f"           (created: {timeline.current_belief.created_at[:10]}, sim={timeline.current_belief.similarity:.3f})")
    print(f"  History: {len(timeline.history)} items")
    for h in timeline.history[:8]:
        flag = " ⚡superseded" if h.superseded_in_conversation else ""
        print(f"    {h.created_at[:10]} [{h.node_type:9s}] {h.text[:65]}{flag}")

    storage.close()


if __name__ == "__main__":
    run_ablation()
