"""
Data models for extraction output — v2 (observation engine architecture).

Three node types by processing semantics:
- stance: supersedable positions (→ supersession detection pipeline)
- event: immutable happenings (→ accumulation/pattern pipeline)
- intention: stated plans (→ fulfillment tracking pipeline)

Aligned with storage schema and ARCHITECTURE.md §4.1.
"""

from dataclasses import dataclass
from typing import Optional

# Single source of truth for valid node types — used by extraction AND storage
VALID_NODE_TYPES = {"stance", "event", "intention"}

# Valid timeframes for event-type propositions
VALID_EVENT_TIMEFRAMES = {"recent", "historical", "ongoing"}


@dataclass
class Proposition:
    """A single atomic proposition extracted from user text."""

    proposition: str
    node_type: str  # stance | event | intention
    confidence: float  # 0.0–1.0
    supersedable: bool  # True if this could be replaced by future understanding
    event_timeframe: Optional[str] = None  # recent | historical | ongoing (events only)

    def __post_init__(self):
        """Validate field values."""
        if self.node_type not in VALID_NODE_TYPES:
            # Graceful fallback: unknown types default to event
            self.node_type = "event"

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0–1.0, got {self.confidence}")

        if not self.proposition or not self.proposition.strip():
            raise ValueError("Proposition text cannot be empty")

        # Validate event_timeframe
        if self.node_type == "event" and self.event_timeframe is not None:
            if self.event_timeframe not in VALID_EVENT_TIMEFRAMES:
                self.event_timeframe = "recent"  # Safe default
        elif self.node_type != "event":
            self.event_timeframe = None  # Only events have timeframes


class ExtractionError(Exception):
    """Raised when extraction fails."""

    pass
