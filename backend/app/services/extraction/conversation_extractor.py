"""
Conversation-level extraction service — Mode 2 (retrospective).

Sends the ENTIRE conversation as one LLM call. The model reads the full
dialogue arc and extracts propositions that survived the conversation,
applying the five validity constraints.

This produces fewer, richer propositions than per-message extraction
because the LLM can see how thinking resolved across the conversation.

Design reference: ARCHITECTURE.md §1, §5, CONTINUE.md
"""

import json
from typing import List, Optional
from dataclasses import dataclass

from app.services.providers.base import Provider, ProviderError
from .models import Proposition, ExtractionError
from .prompt_conversation import (
    CONVERSATION_EXTRACTION_SYSTEM,
    build_conversation_prompt,
)


@dataclass
class ConversationExtractionResult:
    """Result of extracting from a full conversation."""
    conversation_summary: str
    propositions: List[Proposition]


class ConversationExtractionService:
    """Extracts propositions from a complete conversation in one LLM call.

    Unlike per-message ExtractionService, this sends the entire conversation
    and lets the model apply constraints with full dialogue context.
    """

    def __init__(self, provider: Provider):
        self.provider = provider

    async def extract(
        self,
        conversation_text: str,
    ) -> ConversationExtractionResult:
        """
        Extract propositions from a complete conversation.

        Args:
            conversation_text: The full formatted conversation
                (both user and AI messages, clearly labeled).

        Returns:
            ConversationExtractionResult with summary and propositions.

        Raises:
            ProviderError: If LLM call fails
            ExtractionError: If response doesn't match schema
        """
        prompt = build_conversation_prompt(conversation_text)

        try:
            raw_response = await self.provider.complete(
                prompt=prompt,
                system_prompt=CONVERSATION_EXTRACTION_SYSTEM,
                max_tokens=8192,  # Conversation-level needs more output tokens than per-message
            )
        except ProviderError as e:
            raise e

        # Parse JSON response — handle markdown fences if present
        raw_text = raw_response.strip()
        if raw_text.startswith("```"):
            # Strip markdown code fences
            lines = raw_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\n".join(lines)

        try:
            response_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise ExtractionError(
                f"LLM returned invalid JSON: {raw_text[:300]}..."
            ) from e

        if "propositions" not in response_data:
            raise ExtractionError(
                f"Response missing 'propositions' key: {list(response_data.keys())}"
            )

        if not isinstance(response_data["propositions"], list):
            raise ExtractionError(
                f"'propositions' must be a list, got {type(response_data['propositions'])}"
            )

        conversation_summary = response_data.get("conversation_summary", "")

        propositions = []
        for i, prop_dict in enumerate(response_data["propositions"]):
            try:
                proposition = Proposition(
                    proposition=prop_dict["proposition"],
                    node_type=prop_dict["node_type"],
                    confidence=prop_dict["confidence"],
                    supersedable=prop_dict.get("supersedable", True),
                    event_timeframe=prop_dict.get("event_timeframe"),
                    superseded_in_conversation=prop_dict.get(
                        "superseded_in_conversation", False
                    ),
                )
                propositions.append(proposition)
            except KeyError as e:
                raise ExtractionError(
                    f"Proposition {i} missing required field: {e}"
                ) from e
            except ValueError as e:
                raise ExtractionError(
                    f"Proposition {i} validation failed: {e}"
                ) from e

        return ConversationExtractionResult(
            conversation_summary=conversation_summary,
            propositions=propositions,
        )
