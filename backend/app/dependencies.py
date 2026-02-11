"""
FastAPI dependency injection — provides service instances per request.

Rewritten for SQLite architecture. Will be populated as components are built.
"""

from app.services.router import get_provider
from app.services.extraction.extractor import ExtractionService


def get_extraction_service() -> ExtractionService:
    """Create ExtractionService instance with default provider."""
    provider = get_provider(task="reasoning", sensitive=False)
    return ExtractionService(provider)


# TODO: Add storage, embedding, ingestion dependencies (Components 1.2-1.4)
