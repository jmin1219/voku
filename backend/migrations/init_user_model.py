"""
Piece 1: Initialize user model schema + seed dimensions + evidence_mode column.

Creates user_model and model_evidence tables, adds evidence_mode to propositions,
and seeds the 4 universal dimensions.

Usage:
  cd backend
  python3 -m migrations.init_user_model

Idempotent — safe to run multiple times.
"""

from pathlib import Path

from app.services.user_model.storage import UserModelStorage

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "voku.db"
SEEDS_PATH = DATA_DIR / "dimension_seeds.json"


def main():
    print("=== Piece 1: User Model Initialization ===\n")

    storage = UserModelStorage(DB_PATH)

    # 1. Add evidence_mode column to propositions (idempotent)
    storage.add_evidence_mode_column()
    print("✅ evidence_mode column ensured on propositions table")

    # 2. Seed dimensions (idempotent — skips existing)
    storage.seed_dimensions(SEEDS_PATH)
    dims = storage.get_all_dimensions()
    print(f"✅ {len(dims)} seed dimensions active:")
    for d in dims:
        print(f"   {d.id}: {d.dimension} ({d.decay_class}) — confidence {d.confidence}")

    # 3. Verify model_evidence table exists
    count = storage._conn.execute("SELECT COUNT(*) FROM model_evidence").fetchone()[0]
    print(f"✅ model_evidence table ready ({count} assignments)")

    # 4. Check unassigned propositions
    unassigned = storage.get_unassigned_propositions()
    print(f"\n📊 {len(unassigned)} propositions awaiting assignment")

    storage.close()
    print("\n✅ Piece 1 complete.")


if __name__ == "__main__":
    main()
