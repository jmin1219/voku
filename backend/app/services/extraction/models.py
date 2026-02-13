"""
Data models for extraction output.

Aligned with storage schema — same field names, same enums, same confidence format.
See prompt.py for the five node_type values.
"""

from dataclasses import dataclass
from typing import Optional

# Single source of truth for valid node types — used by extraction AND storage
VALID_NODE_TYPES = {"belief", "observation", "pattern", "intention", "decision"}


@dataclass
class Proposition:
    """A single atomic proposition extracted from user text."""

    proposition: str
    node_type: str  # belief | observation | pattern | intention | decision
    confidence: float  # 0.0–1.0
    structured_data: Optional[dict] = None

    def __post_init__(self):
        """Validate field values."""
        if self.node_type not in VALID_NODE_TYPES:
            self.node_type = "observation"

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0–1.0, got {self.confidence}")

        if not self.proposition or not self.proposition.strip():
            raise ValueError("Proposition text cannot be empty")


class ExtractionError(Exception):
    """Raised when extraction fails."""
    pass
