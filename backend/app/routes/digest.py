"""
Temporal digest routes — AI-synthesized narratives from the trace graph.

POST /api/digest        → generate period summary (stored as system trace)
GET  /api/digest/evolution → trace topic evolution (ephemeral)

Design: TASKS_PHASE7.md § Task 7.4, Task 7.6
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.dependencies import digest_service
from app.routes.traces import invalidate_trace_cache


router = APIRouter(prefix="/api", tags=["digest"])


class DigestRequest(BaseModel):
    days: int = 30


@router.post("/digest")
async def generate_digest(request: DigestRequest):
    """Generate an AI-synthesized narrative for a time period.

    The narrative is stored as a system trace — retrievable in future
    context assembly. Returns the narrative + trace metadata.
    """
    try:
        digest_trace = await digest_service.generate_period_summary(
            days=request.days
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # New system trace was stored + embedded — invalidate phase space cache
    invalidate_trace_cache()

    return {
        "id": digest_trace.id,
        "narrative": digest_trace.content,
        "conversation_id": digest_trace.conversation_id,
        "timestamp": digest_trace.timestamp,
        "source": digest_trace.source,
    }


@router.get("/digest/evolution")
async def get_topic_evolution(
    q: str = Query(..., description="Topic to trace evolution for"),
    days: int = Query(60, description="Lookback window in days"),
):
    """Trace how thinking about a topic evolved over time.

    On-demand, not stored. Returns the narrative directly.
    """
    try:
        narrative = await digest_service.get_topic_evolution(
            query=q, days=days
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "query": q,
        "days": days,
        "narrative": narrative,
    }
