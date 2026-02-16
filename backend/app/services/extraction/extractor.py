"""
Extraction service — converts user text into structured propositions.

v2: Supports conversation context (preceding AI message) for comprehension.
The AI context helps the LLM understand what the user is responding to,
but propositions are only extracted from the user's message.
"""

import json
from typing import List, Optional

from app.services.providers.base import Provider, ProviderError
from .models import Proposition, ExtractionError
from .prompt import EXTRACTION_SYSTEM_PROMPT, CONTEXT_PREFIX


class ExtractionService:
    """Extracts structured propositions from user text using LLM."""

    def __init__(self, provider: Provider):
        self.provider = provider

    async def extract(
        self,
        user_text: str,
        ai_context: Optional[str] = None,
    ) -> List[Proposition]:
        """
        Extract atomic propositions from user text.

        Args:
            user_text: The user's message to extract from.
            ai_context: Optional preceding AI message for comprehension context.
                        Used to understand what the user is responding to.
                        NOT extracted from — only the user's message produces propositions.

        Returns only explicitly stated propositions (Constraint 0.3).

        Raises:
            ProviderError: If LLM call fails
            ExtractionError: If response doesn't match schema
        """
        # Build the prompt: optionally prepend AI context for comprehension
        if ai_context:
            prompt = CONTEXT_PREFIX.format(ai_context=ai_context[:2000]) + user_text
        else:
            prompt = user_text

        try:
            raw_response = await self.provider.complete(
                prompt=prompt, system_prompt=EXTRACTION_SYSTEM_PROMPT
            )
        except ProviderError as e:
            raise e

        try:
            response_data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise ExtractionError(
                f"LLM returned invalid JSON: {raw_response[:200]}..."
            ) from e

        if "propositions" not in response_data:
            raise ExtractionError(
                f"Response missing 'propositions' key: {response_data}"
            )

        if not isinstance(response_data["propositions"], list):
            raise ExtractionError(
                f"'propositions' must be a list, got {type(response_data['propositions'])}"
            )

        propositions = []
        for i, prop_dict in enumerate(response_data["propositions"]):
            try:
                proposition = Proposition(
                    proposition=prop_dict["proposition"],
                    node_type=prop_dict["node_type"],
                    confidence=prop_dict["confidence"],
                    supersedable=prop_dict.get("supersedable", True),
                    event_timeframe=prop_dict.get("event_timeframe"),
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

        return propositions
