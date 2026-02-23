"""
Run exhale on all 4 seed dimensions.

First exhale: dimensions go from estimate="" / confidence=0.0
to populated estimates based on all accumulated evidence.

Usage:
    cd backend
    . venv/bin/activate
    python -m migrations.run_exhale
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.user_model.storage import UserModelStorage
from app.services.embedding.bge import BGEBaseEmbedding
from app.services.providers.groq_provider import GroqProvider
from app.services.user_model.inference import ExhaleService


async def main():
    print("=== Exhale: First Run on All Dimensions ===\n")

    storage = UserModelStorage(settings.db_path)
    embedder = BGEBaseEmbedding()
    provider = GroqProvider()
    service = ExhaleService(storage, embedder, provider)

    # Show current state
    dims = storage.get_all_dimensions()
    print(f"Dimensions: {len(dims)}")
    for d in dims:
        evidence = storage.get_evidence_for_dimension(d.id)
        print(f"  {d.id}: estimate={'(empty)' if not d.estimate else d.estimate[:60]+'...'}, "
              f"confidence={d.confidence}, evidence={len(evidence)}")
    print()

    # Run exhale on all
    result = await service.exhale_all()

    print(f"\n=== Results ===")
    print(f"Updated: {result.updated}, Skipped: {result.skipped}, Errors: {result.errors}\n")

    for r in result.results:
        print(f"--- {r.dimension_id} ---")
        print(f"  Gate: {'✅ PASSED' if r.gate_passed else f'❌ {r.gate_reason}'}")
        print(f"  Confidence: {r.old_confidence:.2f} → {r.new_confidence:.2f}")
        print(f"  Uncertainty: {r.uncertainty_type}")
        print(f"  Evidence: {r.evidence_count} points")
        print(f"  Goals: {r.goal_ids}")
        print(f"  Estimate: {r.new_estimate[:200]}...")
        print(f"  Trace: {r.reasoning_trace[:200]}...")
        print()

    # Verify DB state
    print("=== Post-Exhale State ===")
    dims = storage.get_all_dimensions()
    for d in dims:
        print(f"  {d.id}: confidence={d.confidence}, type={d.uncertainty_type}, "
              f"estimate={d.estimate[:80]}..." if d.estimate else f"  {d.id}: (still empty)")
    print()

    storage.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
