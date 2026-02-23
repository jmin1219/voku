"""
FastAPI dependency injection — shared service singletons.

The proposition stack (storage, embedder, retrieval) must be shared
across routes so the in-memory embedding cache stays consistent.
When extract.py stores new propositions, chat.py's retrieval sees them
immediately because they share the same SQLiteStorage instance.
"""

from app.config import settings
from app.services.storage.sqlite_storage import SQLiteStorage
from app.services.embedding.bge import BGEBaseEmbedding
from app.services.retrieval import RetrievalService
from app.services.router import get_provider
from app.services.extraction.extractor import ExtractionService


# --- Shared singletons (loaded once at import time) ---

propositions_storage = SQLiteStorage(settings.propositions_db_path)
embedder = BGEBaseEmbedding()
retrieval = RetrievalService(propositions_storage, embedder)


def get_extraction_service() -> ExtractionService:
    """Create ExtractionService instance with default provider."""
    provider = get_provider(task="reasoning", sensitive=False)
    return ExtractionService(provider)
