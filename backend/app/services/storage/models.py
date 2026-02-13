"""
Storage data models — shared between storage implementations.

Component 1.2 in COMPONENT_SPEC.md.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StoredProposition:
    """A proposition ready for storage, with all metadata."""

    id: str  # UUID
    text: str  # Original proposition text
    node_type: str  # BELIEF/OBSERVATION/PATTERN/INTENTION/DECISION
    confidence: str  # HIGH/MEDIUM/LOW
    source_type: str  # conversation/manual
    created_at: str  # ISO 8601
    session_id: Optional[str] = None
    message_index: Optional[int] = None
    source_char_start: Optional[int] = None
    source_char_end: Optional[int] = None
    source_file: Optional[str] = None
    domain_tags: list[str] = field(default_factory=list)
    status: str = "ACTIVE"  # ACTIVE/SUPERSEDED/CONTRADICTED


@dataclass
class SimilarResult:
    """A proposition returned from similarity search, with its score."""

    proposition: StoredProposition
    score: float  # Cosine similarity (0.0 to 1.0)
