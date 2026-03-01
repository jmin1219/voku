"""
Traces API — serves all traces with positions for the phase space.

GET /api/traces
  Returns nodes with semantic + temporal positions, clusters, k-NN edges,
  and stored connections (temporal + semantic from ConnectionService).
  Cached in memory; invalidated when new traces are embedded.

POST /api/traces/connections/compute
  Recomputes temporal + semantic connections. Called after seeding or
  when connection quality needs refreshing.

v2 replacement for routes/propositions.py.
"""

import threading

from fastapi import APIRouter

from app.dependencies import trace_storage
from app.services.trace_projection import compute_trace_projection
from app.services.connections import ConnectionService
from app.services.patterns import PatternService

router = APIRouter(prefix="/api", tags=["traces"])

_cache: dict | None = None
_lock = threading.Lock()


def invalidate_trace_cache():
    """Called after new traces are embedded to force recomputation."""
    global _cache
    _cache = None


@router.get("/phase-space")
def get_phase_space():
    """Return all traces with multi-resolution data for the phase space.

    Response contains traces (nodes), fine clusters, orientations, and edges.
    Alias for /traces with identical data.
    """
    return get_traces()


@router.get("/traces")
def get_traces():
    """Return all traces with positions, clusters, and edges for phase space."""
    global _cache
    with _lock:
        if _cache is None:
            projection = compute_trace_projection(trace_storage)

            # Merge stored connections (temporal + semantic from ConnectionService)
            # alongside k-NN edges from projection
            stored_connections = []
            for conn_type in ("temporal", "semantic"):
                conns = trace_storage.get_connections_by_type(conn_type)
                for c in conns:
                    stored_connections.append({
                        "source": c.source_id,
                        "target": c.target_id,
                        "type": c.type,
                        "weight": c.weight,
                    })

            _cache = {
                **projection,
                "connections": stored_connections,
            }
        return _cache


@router.post("/traces/connections/compute")
def compute_connections():
    """Recompute all connections from current trace data."""
    service = ConnectionService(trace_storage)
    result = service.compute_all(k=5, threshold=0.3)

    # Invalidate cache so next GET /traces includes new connections
    invalidate_trace_cache()

    return {
        "status": "ok",
        "temporal_connections": result["temporal"],
        "semantic_connections": result["semantic"],
    }


@router.get("/patterns")
def get_patterns(days: int = 14):
    """Detect recurring annotation patterns within a timeframe."""
    service = PatternService(trace_storage)
    patterns = service.detect_patterns(days=days)
    return {
        "patterns": [
            {
                "type": p.type,
                "description": p.description,
                "trace_ids": p.trace_ids,
                "timeframe": p.timeframe,
                "confidence": p.confidence,
            }
            for p in patterns
        ],
        "meta": {"days": days, "count": len(patterns)},
    }


@router.get("/traces/{trace_id}")
def get_trace(trace_id: str):
    """Get a single trace with its annotations and connections."""
    trace = trace_storage.get_trace(trace_id)
    if trace is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    annotations = trace_storage.get_annotations_for_trace(trace_id)
    connections = trace_storage.get_connections_for_trace(trace_id)

    return {
        "id": trace.id,
        "timestamp": trace.timestamp,
        "content": trace.content,
        "conversationId": trace.conversation_id,
        "parentTraceId": trace.parent_trace_id,
        "source": trace.source,
        "annotations": [
            {
                "id": a.id,
                "type": a.type,
                "key": a.key,
                "value": a.value,
                "confidence": a.confidence,
            }
            for a in annotations
        ],
        "connections": [
            {
                "sourceId": c.source_id,
                "targetId": c.target_id,
                "type": c.type,
                "weight": c.weight,
            }
            for c in connections
        ],
    }
