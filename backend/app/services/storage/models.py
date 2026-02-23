"""
Storage data models — shared between storage implementations.

v2: Aligned with observation engine architecture.
- node_type: stance | event | intention (was: belief | observation | pattern | intention | decision)
- Added: event_timeframe, supersedable, message_position, source_type enum
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StoredProposition:
    """A proposition ready for storage, with all metadata."""

    id: str  # UUID
    text: str  # Original proposition text
    node_type: str  # stance | event | intention
    confidence: float  # 0.0–1.0
    source_type: str  # conversation | user_declared | standalone_text
    created_at: str  # ISO 8601
    supersedable: bool = True  # Can this be replaced by future understanding?
    event_timeframe: Optional[str] = None  # recent | historical | ongoing (events only)
    superseded_in_conversation: bool = False  # True if position changed within same conversation
    conversation_summary: Optional[str] = None  # Summary from conversation-level extraction
    session_id: Optional[str] = None
    message_index: Optional[int] = None
    message_position: Optional[int] = None  # Position in conversation (earlier = less AI-mediated)
    source_char_start: Optional[int] = None
    source_char_end: Optional[int] = None
    source_file: Optional[str] = None
    domain_tags: list[str] = field(default_factory=list)
    status: str = "active"  # active | superseded | contradicted


@dataclass
class SimilarResult:
    """A proposition returned from similarity search, with its score."""

    proposition: StoredProposition
    score: float  # Cosine similarity (0.0 to 1.0)
