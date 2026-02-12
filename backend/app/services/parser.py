"""
Conversation import parser — parses Claude conversation exports into structured messages.

Component 1.1 in COMPONENT_SPEC.md.
"""

from pathlib import Path

from backend.app.models.proposition import ConversationMessage


class ConversationParser:
    def parse_file(self, filepath: Path) -> list[ConversationMessage]:
        raise NotImplementedError

    def parse_directory(self, dirpath: Path) -> list[ConversationMessage]:
        raise NotImplementedError
