"""
Run Assignment Pass 1 on all unassigned propositions.

Reads unassigned propositions from voku.db, classifies each into 0-3
of the 4 seed dimensions via Groq, stores assignments in model_evidence,
and updates evidence_mode on propositions.

Usage:
  cd backend
  python3 -m migrations.run_assignment_p1
"""

import asyncio
from pathlib import Path

from app.services.user_model.storage import UserModelStorage
from app.services.user_model.assignment import AssignmentService
from app.services.providers.groq_provider import GroqProvider

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "voku.db"
SEEDS_PATH = DATA_DIR / "dimension_seeds.json"


async def main():
    print("=== Assignment Pass 1: Classify propositions into dimensions ===\n")

    # Setup
    storage = UserModelStorage(DB_PATH)
    provider = GroqProvider()
    service = AssignmentService(provider)

    # Get dimensions and unassigned propositions
    dimensions = storage.get_all_dimensions()
    unassigned = storage.get_unassigned_propositions()

    print(f"Active dimensions: {[d.id for d in dimensions]}")
    print(f"Unassigned propositions: {len(unassigned)}\n")

    if not unassigned:
        print("Nothing to assign. Done.")
        storage.close()
        return

    # Run assignment
    result = await service.assign_batch(unassigned, dimensions)

    print(f"\n=== Results ===")
    print(f"Assignments created: {len(result.assignments)}")
    print(f"Propositions skipped (0 dimensions): {result.skipped}")
    print(f"Errors: {result.errors}")

    # Store assignments
    if result.assignments:
        storage.store_assignments(result.assignments)
        print(f"\n✅ {len(result.assignments)} assignments stored in model_evidence")

    # Update evidence_mode on propositions
    mode_updates = 0
    for prop_id, mode in result.evidence_modes.items():
        storage._conn.execute(
            "UPDATE propositions SET evidence_mode = ? WHERE id = ?",
            (mode, prop_id),
        )
        mode_updates += 1
    storage._conn.commit()
    print(f"✅ {mode_updates} propositions updated with evidence_mode")

    # Print distribution
    print(f"\n=== Dimension distribution ===")
    for dim in dimensions:
        d = storage.get_dimension(dim.id)
        print(f"  {d.id}: {d.evidence_count} propositions")

    remaining = storage.get_unassigned_propositions()
    print(f"\n  Unassigned: {len(remaining)} propositions")

    # Print evidence mode distribution
    exp_count = storage._conn.execute(
        "SELECT COUNT(*) FROM propositions WHERE evidence_mode = 'experiential'"
    ).fetchone()[0]
    retro_count = storage._conn.execute(
        "SELECT COUNT(*) FROM propositions WHERE evidence_mode = 'retrospective'"
    ).fetchone()[0]
    print(f"\n=== Evidence mode distribution ===")
    print(f"  Experiential: {exp_count}")
    print(f"  Retrospective: {retro_count}")

    storage.close()
    print("\n✅ Assignment Pass 1 complete.")


if __name__ == "__main__":
    asyncio.run(main())
