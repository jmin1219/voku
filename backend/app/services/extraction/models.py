"""
Data models for extraction output.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Proposition:
    """
    A single atomic proposition extracted from user text.
    
    Attributes:
        proposition: Human-readable summary/observation in user's voice
        node_purpose: Type of proposition (observation, belief, pattern, intention, decision)
        confidence: Model's confidence in extraction (0.0-1.0)
        source_type: Whether explicitly stated or inferred from context
        structured_data: Optional structured data for metrics/quantities
    """
    proposition: str
    node_purpose: str
    confidence: float
    source_type: str
    structured_data: Optional[dict] = None
    
    def __post_init__(self):
        """Validate field values."""
        # Validate node_purpose
        valid_purposes = {"observation", "belief", "pattern", "intention", "decision"}
        if self.node_purpose not in valid_purposes:
            raise ValueError(
                f"Invalid node_purpose '{self.node_purpose}'. Must be one of: {valid_purposes}"
            )
        
        # Validate source_type
        valid_sources = {"explicit", "inferred"}
        if self.source_type not in valid_sources:
            raise ValueError(
                f"Invalid source_type '{self.source_type}'. Must be one of: {valid_sources}"
            )
        
        # Validate confidence range
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        # Validate proposition is not empty
        if not self.proposition or not self.proposition.strip():
            raise ValueError("Proposition text cannot be empty")


class ExtractionError(Exception):
    """Raised when extraction fails."""
    pass
