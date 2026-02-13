"""
Extraction service — converts user text into structured propositions.
"""

import json
from typing import List

from app.services.providers.base import Provider, ProviderError
from .models import Proposition, ExtractionError
from .prompt import EXTRACTION_SYSTEM_PROMPT


class ExtractionService:
    """Extracts structured propositions from user text using LLM."""

    def __init__(self, provider: Provider):
        self.provider = provider

    async def extract(self, user_text: str) -> List[Proposition]:
        """
        Extract atomic propositions from user text.

        Returns only explicitly stated propositions (Constraint 0.3).

        Raises:
            ProviderError: If LLM call fails
            ExtractionError: If response doesn't match schema
        """
        try:
            raw_response = await self.provider.complete(
                prompt=user_text, system_prompt=EXTRACTION_SYSTEM_PROMPT
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
                    structured_data=prop_dict.get("structured_data"),
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
