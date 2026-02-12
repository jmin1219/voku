"""
Shared data models for propositions and conversation messages.

Components 1.1, 1.2, 1.4 in COMPONENT_SPEC.md.
"""

from datetime import datetime
from dataclasses import dataclass


@dataclass
class ConversationMessage:
    text: str  # Raw message text (thinking/tool blocks stripped for assistant)
    speaker: str  # "user" or "assistant" (from "Prompt:"/"Response:")
    timestamp: datetime  # Parsed from US locale line: "M/D/YYYY, H:MM:SS AM/PM"
    session_id: str  # UUID extracted from Link header (e.g., "9a9c2191-84b1-...")
    message_index: int  # Order within conversation
    source_char_start: int  # Character offset of message start in original export file
    source_char_end: int  # Character offset of message end in original export file
    source_file: str  # Filename of the source export (for multi-file provenance)
    assistant_reasoning: (
        str | None
    )  # Extracted thinking blocks (for future eval comparison)
