"""
Propositions API — serves all propositions with 3D positions for the phase space.

GET /api/propositions
  Returns nodes with semantic + temporal positions, clusters, and dimension assignments.
  Cached in memory; recomputed after extraction via invalidate_cache().
  
  Lock serializes concurrent requests to prevent UMAP/numba threading crashes.
  React Strict Mode fires double-mounts in dev, so concurrent calls are expected.
"""

import threading

from fastapi import APIRouter

from app.dependencies import propositions_storage
from app.services.projection import compute_projection

router = APIRouter(prefix="/api", tags=["propositions"])

_cache: dict | None = None
_lock = threading.Lock()


def invalidate_cache():
    """Called after extraction to force recomputation on next request."""
    global _cache
    _cache = None


@router.get("/propositions")
def get_propositions():
    """Return all propositions with 3D positions, clusters, and dimension coloring."""
    global _cache
    with _lock:
        if _cache is None:
            _cache = compute_projection(propositions_storage.db_path)
        return _cache
