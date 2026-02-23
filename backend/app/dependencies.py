"""
FastAPI dependency injection — shared service singletons.

The proposition stack (storage, embedder, retrieval) must be shared
across routes so the in-memory embedding cache stays consistent.
When extract.py stores new propositions, chat.py's retrieval sees them
immediately because they share the same SQLiteStorage instance.

Build 4 adds user model singletons: UserModelStorage shares the same DB,
ContextAssemblyV2 wires model intelligence into chat context.
"""

from app.config import settings
from app.services.storage.sqlite_storage import SQLiteStorage
from app.services.embedding.bge import BGEBaseEmbedding
from app.services.retrieval import RetrievalService
from app.services.router import get_provider
from app.services.extraction.extractor import ExtractionService
from app.services.user_model.storage import UserModelStorage
from app.services.user_model.context import ContextAssemblyV2


# --- Shared singletons (loaded once at import time) ---

propositions_storage = SQLiteStorage(settings.db_path)
embedder = BGEBaseEmbedding()
retrieval = RetrievalService(propositions_storage, embedder)

# User model — shares same DB as propositions (after Piece 0 consolidation)
user_model_storage = UserModelStorage(settings.db_path)
context_assembly = ContextAssemblyV2(user_model_storage, retrieval, embedder)


def get_extraction_service() -> ExtractionService:
    """Create ExtractionService instance with default provider."""
    provider = get_provider(task="reasoning", sensitive=False)
    return ExtractionService(provider)
