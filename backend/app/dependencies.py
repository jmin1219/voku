"""
FastAPI dependency injection — shared service singletons.

v2 trace-based singletons used by chat.py.
v1 proposition-based singletons kept for extract.py and propositions.py
until those routes are dropped.

All singletons share the same embedder and DB path.
"""

from app.config import settings
from app.services.embedding.bge import BGEBaseEmbedding

# --- Shared across v1 and v2 ---
embedder = BGEBaseEmbedding()

# --- v2 trace-based singletons (used by chat.py) ---
from app.services.storage.sqlite_trace import SQLiteTraceStorage
from app.services.trace_retrieval import TraceRetrievalService
from app.services.trace_context import TraceContextAssembly
from app.services.annotation import AnnotationExtractionService
from app.services.connections import ConnectionService
from app.services.contradiction import ContradictionDetector
from app.services.router import get_provider

trace_storage = SQLiteTraceStorage(settings.db_path)
trace_retrieval = TraceRetrievalService(trace_storage, embedder)
contradiction_detector = ContradictionDetector(trace_storage)
trace_context = TraceContextAssembly(trace_retrieval, contradiction_detector=contradiction_detector)
annotation_service = AnnotationExtractionService(get_provider())
connection_service = ConnectionService(trace_storage)

# --- v1 proposition-based singletons (DISABLED — v2 trace architecture) ---
# Commented out to prevent import crash: v1 StorageService ABC and
# StoredProposition model were removed when __init__.py was rewritten.
# These routes (extract.py, propositions.py) are not needed for v2 demo.
# Restore if v1 routes are ever re-enabled.
#
# from app.services.storage.sqlite_storage import SQLiteStorage
# from app.services.retrieval import RetrievalService
# from app.services.router import get_provider
# from app.services.extraction.extractor import ExtractionService
# from app.services.user_model.storage import UserModelStorage
# from app.services.user_model.context import ContextAssemblyV2
#
# propositions_storage = SQLiteStorage(settings.db_path)
# retrieval = RetrievalService(propositions_storage, embedder)
# user_model_storage = UserModelStorage(settings.db_path)
# context_assembly = ContextAssemblyV2(user_model_storage, retrieval, embedder)
#
#
# def get_extraction_service() -> ExtractionService:
#     """Create ExtractionService instance with default provider."""
#     provider = get_provider(task="reasoning", sensitive=False)
#     return ExtractionService(provider)
