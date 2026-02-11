"""
Voku — Personal context engine with temporal belief tracking.

Backend entry point. Extraction pipeline + SQLite storage + MCP server.
"""

from contextlib import asynccontextmanager

from app.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    from pathlib import Path

    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # TODO: Initialize SQLite storage (Component 1.2)
    # TODO: Initialize embedding service (Component 1.3)

    yield

    # Shutdown cleanup


app = FastAPI(title="Voku", version="0.4.0", lifespan=lifespan)

# CORS (development only)
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/")
def read_root():
    return {"name": "Voku", "version": "0.4.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
