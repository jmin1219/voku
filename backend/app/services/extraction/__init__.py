"""
Extraction service - converts conversation turns into atomic propositions.
"""
from .extractor import ExtractionService
from .models import Proposition, ExtractionError

__all__ = ["ExtractionService", "Proposition", "ExtractionError"]
