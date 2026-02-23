"""
Run Assignment Pass 2 — score relevance + direction on existing assignments.

Reads all assignments from model_evidence, scores each (proposition, dimension)
pair via Groq, updates relevance and direction in place.

Usage:
  cd backend
  python3 -m migrations.run_assignment_p2
"""

import asyncio
from collections import Counter
from pathlib import Path

from app.services.user_model.storage import UserModelStorage
from app.services.user_model.assignment import AssignmentService
from app.services.providers.groq_provider import GroqProvider

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "voku.db"


async def main():
    print("=== Assignment Pass 2: Score relevance + direction ===\n")

    storage = UserModelStorage(DB_PATH)
    provider = GroqProvider()
    service = AssignmentService(provider)

    # Get dimension descriptions for prompt context
    dimensions = storage.get_all_dimensions()
    dim_descriptions = {d.id: d.description for d in dimensions}

    # Get all assignments (joined with proposition text)
    assignments = storage.get_all_assignments()
    print(f"Assignments to score: {len(assignments)}\n")

    if not assignments:
        print("Nothing to score. Done.")
        storage.close()
        return

    # Run scoring
    result = await service.score_batch(assignments, dim_descriptions)

    print(f"\n=== Results ===")
    print(f"Scores returned: {len(result.scores)}")
    print(f"Errors: {result.errors}")

    # Apply scores to database
    if result.scores:
        updates = [
            (s.model_id, s.proposition_id, s.relevance, s.direction)
            for s in result.scores
        ]
        storage.update_assignments_batch(updates)
        print(f"\n✅ {len(updates)} assignments updated")

    # Print distribution
    relevance_buckets = Counter()
    direction_counts = Counter()
    for s in result.scores:
        if s.relevance >= 0.8:
            relevance_buckets["high (0.8-1.0)"] += 1
        elif s.relevance >= 0.5:
            relevance_buckets["medium (0.5-0.79)"] += 1
        else:
            relevance_buckets["low (0.0-0.49)"] += 1
        direction_counts[s.direction] += 1

    print(f"\n=== Relevance distribution ===")
    for bucket, count in sorted(relevance_buckets.items()):
        print(f"  {bucket}: {count}")

    print(f"\n=== Direction distribution ===")
    for direction, count in sorted(direction_counts.items()):
        print(f"  {direction}: {count}")

    # Per-dimension stats
    print(f"\n=== Per-dimension average relevance ===")
    dim_scores: dict[str, list[float]] = {}
    for s in result.scores:
        dim_scores.setdefault(s.model_id, []).append(s.relevance)
    for dim_id in sorted(dim_scores):
        scores = dim_scores[dim_id]
        avg = sum(scores) / len(scores)
        print(f"  {dim_id}: avg {avg:.2f} ({len(scores)} assignments)")

    storage.close()
    print("\n✅ Assignment Pass 2 complete.")


if __name__ == "__main__":
    asyncio.run(main())
