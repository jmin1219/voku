"""
FastAPI dependency injection - provides service instances per request.
"""

import kuzu
from app.services.chat import ChatService
from app.services.extraction.extractor import ExtractionService
from app.services.graph.operations import GraphOperations
from app.services.router import get_provider
from fastapi import Depends, Request


def get_database(request: Request) -> kuzu.Database:
    """Get database from app state (initialized in lifespan at startup)."""
    return request.app.state.db


def get_graph_ops(db: kuzu.Database = Depends(get_database)) -> GraphOperations:
    """Get GraphOperations instance. (Kuzu connections aren't thread-safe, so we create a new instance per request.)"""
    return GraphOperations(db)


def get_extraction_service() -> ExtractionService:
    """Create ExtractionService instance with default provider."""
    provider = get_provider(task="reasoning", sensitive=False)
    return ExtractionService(provider)


def get_chat_service(
    graph_ops: GraphOperations = Depends(get_graph_ops),
    extraction: ExtractionService = Depends(get_extraction_service),
) -> ChatService:
    """
    Create ChatService with all dependencies injected.

    Dependencies injected by FastAPI:
    - graph_ops: GraphOperations instance with database connection
    - extraction: ExtractionService instance with provider
    """
    provider = get_provider(task="reasoning", sensitive=False)

    return ChatService(
        extraction_service=extraction,
        graph_ops=graph_ops,
        provider=provider,
    )
