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

    yield

    # Shutdown cleanup


app = FastAPI(title="Voku", version="0.4.0", lifespan=lifespan)

# CORS (development only)
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url, "http://localhost:5175"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Conversation-Id"],
    )


# Register routes (v2 trace architecture)
from app.routes.chat import router as chat_router
from app.routes.traces import router as traces_router
app.include_router(chat_router)
app.include_router(traces_router)
# v1 routes disabled — extract.py and propositions.py depend on removed v1 singletons


@app.get("/")
def read_root():
    return {"name": "Voku", "version": "0.4.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
