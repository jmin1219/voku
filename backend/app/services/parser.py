"""
Conversation import parser — parses Claude conversation exports into structured messages.

Component 1.1 in COMPONENT_SPEC.md.
"""

import re
from datetime import datetime
from pathlib import Path

from models.proposition import ConversationMessage

# Regex patterns
SESSION_ID_PATTERN = re.compile(r"https://claude\.ai/chat/([a-f0-9-]+)")
MESSAGE_HEADING_PATTERN = re.compile(r"^## (Prompt|Response):\s*$", re.MULTILINE)
BASE64_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(data:image/[^)]+\)")
FENCED_BLOCK_PATTERN = re.compile(r"````plaintext\n.*?````", re.DOTALL)
FOOTER_PATTERN = re.compile(
    r"\n---\s*\nPowered by \[Claude Exporter\]\([^)]+\)\s*$"
)


class ConversationParser:
    def parse_file(self, filepath: Path) -> list[ConversationMessage]:
        """Parse a single Claude Exporter markdown file into structured messages."""
        raw = filepath.read_text(encoding="utf-8")
        source_file = filepath.name

        # Extract session_id from Link header
        session_match = SESSION_ID_PATTERN.search(raw)
        if not session_match:
            raise ValueError(f"No session_id found in {filepath}")
        session_id = session_match.group(1)

        # Strip footer
        raw_clean = FOOTER_PATTERN.sub("", raw)

        # Find all message headings and their positions
        headings = list(MESSAGE_HEADING_PATTERN.finditer(raw_clean))
        if not headings:
            return []

        messages = []
        for i, heading in enumerate(headings):
            speaker = "user" if heading.group(1) == "Prompt" else "assistant"

            # Content runs from after heading to next heading (or end)
            content_start = heading.end() + 1
            if i + 1 < len(headings):
                content_end = headings[i + 1].start()
            else:
                content_end = len(raw_clean)

            block = raw_clean[content_start:content_end].strip()
            if not block:
                continue

            # First line is the timestamp
            lines = block.split("\n", 1)
            timestamp_str = lines[0].strip()
            try:
                timestamp = datetime.strptime(timestamp_str, "%m/%d/%Y, %I:%M:%S %p")
            except ValueError:
                continue

            # Everything after timestamp is message body
            body = lines[1].strip() if len(lines) > 1 else ""
            if not body:
                continue

            # For assistant messages: extract reasoning, then get text after last block
            assistant_reasoning = None
            if speaker == "assistant":
                # Collect all fenced block content as reasoning
                reasoning_parts = []
                for m in FENCED_BLOCK_PATTERN.finditer(body):
                    inner = m.group(0)
                    inner = re.sub(r"^````plaintext\n", "", inner)
                    inner = re.sub(r"\n?````$", "", inner)
                    inner = inner.strip()
                    if inner:
                        reasoning_parts.append(inner)
                if reasoning_parts:
                    assistant_reasoning = "\n\n".join(reasoning_parts)

                # Find position after the last fenced block
                last_block = None
                for m in FENCED_BLOCK_PATTERN.finditer(body):
                    last_block = m
                if last_block:
                    text = body[last_block.end():].strip()
                else:
                    text = body
            else:
                text = body

            # Strip base64 images
            text = BASE64_IMAGE_PATTERN.sub("", text)

            # Clean up whitespace
            text = re.sub(r"\n{3,}", "\n\n", text).strip()

            if not text:
                continue

            # Char offsets: find where msg.text starts/ends in raw_clean
            # so that raw[start:end] contains msg.text as a substring
            text_pos = raw_clean.find(text, heading.start())
            if text_pos >= 0:
                source_char_start = text_pos
                source_char_end = text_pos + len(text)
            else:
                # Fallback: use full block boundaries
                source_char_start = heading.start()
                source_char_end = content_end

            messages.append(
                ConversationMessage(
                    text=text,
                    speaker=speaker,
                    timestamp=timestamp,
                    session_id=session_id,
                    message_index=len(messages),
                    source_char_start=source_char_start,
                    source_char_end=source_char_end,
                    source_file=source_file,
                    assistant_reasoning=assistant_reasoning,
                )
            )

        return messages

    def parse_directory(self, dirpath: Path) -> list[ConversationMessage]:
        """Parse all .md files in a directory, returning messages from all conversations."""
        messages = []
        for md_file in sorted(dirpath.glob("*.md")):
            messages.extend(self.parse_file(md_file))
        return messages
