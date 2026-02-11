"""
API routes — will be populated as components are built.

Current: placeholder only.
TODO: Add ingestion endpoint (Component 1.4)
TODO: Add retrieval endpoint (Component 2.2)
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/status")
def status():
    """Basic API status check."""
    return {"status": "ok", "architecture": "sqlite", "version": "0.4.0"}
