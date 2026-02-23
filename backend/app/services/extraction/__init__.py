"""
Extraction service - converts conversation turns into atomic propositions.
"""
from .extractor import ExtractionService
from .conversation_extractor import ConversationExtractionService, ConversationExtractionResult
from .models import Proposition, ExtractionError

__all__ = [
    "ExtractionService",
    "ConversationExtractionService",
    "ConversationExtractionResult",
    "Proposition",
    "ExtractionError",
]
