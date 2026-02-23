"""
Propositions API — serves all propositions with 3D positions for the phase space.

GET /api/propositions
  Returns nodes with semantic + temporal positions, clusters, and dimension assignments.
  Cached in memory; recomputed after extraction via invalidate_cache().
"""

from fastapi import APIRouter

from app.dependencies import propositions_storage
from app.services.projection import compute_projection

router = APIRouter(prefix="/api", tags=["propositions"])

_cache: dict | None = None


def invalidate_cache():
    """Called after extraction to force recomputation on next request."""
    global _cache
    _cache = None


@router.get("/propositions")
def get_propositions():
    """Return all propositions with 3D positions, clusters, and dimension coloring."""
    global _cache
    if _cache is None:
        _cache = compute_projection(propositions_storage.db_path)
    return _cache
