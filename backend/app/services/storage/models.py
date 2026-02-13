"""
Storage data models — shared between storage implementations.

Aligned with extraction schema — same node_type enums, float confidence.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StoredProposition:
    """A proposition ready for storage, with all metadata."""

    id: str  # UUID
    text: str  # Original proposition text
    node_type: str  # belief | observation | pattern | intention | decision
    confidence: float  # 0.0–1.0
    source_type: str  # conversation | manual
    created_at: str  # ISO 8601
    session_id: Optional[str] = None
    message_index: Optional[int] = None
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
