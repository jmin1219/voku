"""Conversation data models — raw chat history for the conversation layer."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Conversation:
    id: str
    created_at: str
    updated_at: str


@dataclass
class Message:
    id: str
    conversation_id: str
    role: str  # user | assistant
    content: str
    created_at: str
    thinking: Optional[str] = None  # model reasoning for extraction
