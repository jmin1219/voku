"""
Voku v0.3 — Knowledge-first cognitive prosthetic

Backend entry point. Graph operations + LLM extraction pipeline.
"""

from contextlib import asynccontextmanager

from app.config import settings
from app.routes import chat_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup Logic: Initialize database
    from pathlib import Path

    from app.services.graph.schema import init_database

    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)  # Create data/ directory

    db = init_database(db_path)
    app.state.db = db  # Store db in app state for access in routes/services

    yield  # Run the application

    # Shutdown Logic: Close connections, cleanup resources, etc.
    del app.state.db  # Cleanup database connection


app = FastAPI(title="Voku", version="0.3.0", lifespan=lifespan)

# CORS (development only)
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(chat_router)


@app.get("/")
def read_root():
    return {"name": "Voku", "version": "0.3.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
