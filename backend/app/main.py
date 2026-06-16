"""
Voku — a conversational knowledge graph with temporal retrieval and 3D visualization.

Backend entry point. Trace ingestion + BGE embedding + graph/clustering + phase-space projection.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voku")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Voku starting up...")
    logger.info(f"Database: {db_path}")
    logger.info(f"Provider: {settings.voku_provider}")
    logger.info(f"Environment: {settings.environment}")

    from app.dependencies import embedder
    logger.info(f"Embedding model loaded: {embedder.model_name} ({embedder.dimensions}d)")

    yield

    # Shutdown cleanup


app = FastAPI(title="Voku", version="0.4.0", lifespan=lifespan)

# CORS
if settings.environment == "development":
    cors_origins = [settings.frontend_url, "http://localhost:5175"]
else:
    # Production: use configured origins, or allow same-origin (empty list)
    cors_origins = (
        [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
        if settings.cors_origins
        else []
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-Id"],
)


# Register routes (v2 trace architecture)
from app.routes.chat import router as chat_router
from app.routes.traces import router as traces_router
from app.routes.digest import router as digest_router
app.include_router(chat_router)
app.include_router(traces_router)
app.include_router(digest_router)
# v1 routes disabled — extract.py and propositions.py depend on removed v1 singletons


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# --- Static file serving (production: frontend baked into /app/static) ---
from pathlib import Path

static_dir = Path(__file__).parent.parent / "static"
if static_dir.is_dir() and settings.environment == "production":
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    # Serve index.html at root
    @app.get("/")
    def serve_root():
        return FileResponse(static_dir / "index.html")

    # SPA catch-all: any non-API, non-asset path serves index.html
    # Must be registered AFTER all API routes
    @app.get("/{path:path}")
    def serve_spa(path: str):
        # If the file exists in static dir, serve it (JS, CSS, images)
        file_path = static_dir / path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for SPA routing
        return FileResponse(static_dir / "index.html")
else:
    @app.get("/")
    def read_root():
        return {"name": "Voku", "version": "0.4.0"}
