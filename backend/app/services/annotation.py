"""
Annotation extraction service — LLM-based, async, re-runnable.

Extracts structured annotations from traces using speech act analysis.
No predefined categories — types emerge from what the model finds.

Design: SPEC.md § Annotation Pipeline
Constraint 2.8: Don't classify at all. Annotate.
Constraint 2.11: Annotations are computed, re-extractable.
"""

import json
import uuid
from datetime import datetime, timezone

from app.services.storage.models import Annotation, Trace
from app.services.providers.base import Provider


EXTRACTION_PROMPT = """You are an annotation extractor for a personal knowledge system.

Given a conversational message, extract structured annotations. Each annotation captures
a specific piece of self-knowledge the speaker revealed.

Annotation types emerge from content — common types include:
- "topic": A subject being discussed (key=topic name, value=brief context)
- "decision": A choice the speaker made (key=what was decided, value=the decision)
- "commitment": Something the speaker plans to do (key=the commitment, value=timeframe or detail)
- "measurable": A quantifiable fact (key=what's measured, value=the value)
- "emotion": An emotional state expressed (key=the emotion, value=context)
- "belief": A stated opinion or understanding (key=the belief, value=reasoning if given)
- "question": An unresolved question (key=the question, value=context)

Rules:
- Extract 0-5 annotations per message. Not every message has annotations.
- Only annotate the SPEAKER's self-knowledge, not generic facts.
- Each annotation should be independently meaningful without the full conversation.
- Confidence: 0.9 for explicit statements, 0.7 for clear implications, 0.5 for inferences.
- Use whatever type best fits. You are not limited to the examples above.

Respond with ONLY a JSON array. No other text. Example:
[
  {"type": "decision", "key": "rowing goal", "value": "dropped 2K row target", "confidence": 0.9},
  {"type": "emotion", "key": "frustration", "value": "frustrated with lack of progress on ankle", "confidence": 0.7}
]

If no annotations are extractable, respond with: []"""


class AnnotationExtractionService:
    """Extract annotations from traces using an LLM.

    Uses Groq/Ollama (fast, cheap) — not the chat model.
    Designed to run asynchronously after trace storage.
    """

    def __init__(self, provider: Provider):
        self._provider = provider

    async def extract(
        self,
        trace: Trace,
        conversation_context: list[Trace] | None = None,
    ) -> list[Annotation]:
        """Extract annotations from a single trace.

        Args:
            trace: The trace to annotate.
            conversation_context: Recent traces from the same conversation
                for better extraction (optional, improves quality).

        Returns:
            List of Annotation objects (0-5 per trace).
        """
        user_prompt = self._build_user_prompt(trace, conversation_context)

        try:
            response = await self._provider.complete(
                user_prompt,
                system_prompt=EXTRACTION_PROMPT,
                max_tokens=512,
            )
        except Exception:
            # Extraction failure is non-fatal — trace exists without annotations
            return []

        return self._parse_response(response, trace.id)

    def _build_user_prompt(
        self,
        trace: Trace,
        context: list[Trace] | None,
    ) -> str:
        """Build the user message for the extraction call."""
        parts = []

        if context:
            parts.append("Recent conversation context:")
            for ctx in context[-4:]:  # Last 4 traces for context
                label = "User" if ctx.source == "user" else "Assistant"
                parts.append(f"  {label}: {ctx.content[:300]}")
            parts.append("")

        source_label = "User" if trace.source == "user" else "Assistant"
        parts.append(f"Message to annotate ({source_label}):")
        parts.append(trace.content)

        return "\n".join(parts)

    def _parse_response(self, response: str, trace_id: str) -> list[Annotation]:
        """Parse LLM response into Annotation objects.

        Handles common LLM output issues: markdown fences, preamble text,
        invalid JSON. Returns empty list on parse failure.
        """
        # Strip markdown code fences if present
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return []

        # Groq's json_object mode wraps arrays in an object like {"annotations": [...]}
        # Unwrap: if raw is a dict, find the first list value inside it
        if isinstance(raw, dict):
            for v in raw.values():
                if isinstance(v, list):
                    raw = v
                    break
            else:
                return []  # dict with no list value

        if not isinstance(raw, list):
            return []

        now = datetime.now(timezone.utc).isoformat()
        extractor = f"{self._provider.__class__.__name__}"

        annotations = []
        for item in raw[:5]:  # Cap at 5
            if not isinstance(item, dict):
                continue
            if "type" not in item:
                continue

            annotations.append(Annotation(
                id=str(uuid.uuid4()),
                trace_id=trace_id,
                type=item.get("type", "unknown"),
                key=item.get("key"),
                value=item.get("value"),
                confidence=item.get("confidence", 0.5),
                extracted_at=now,
                extractor=extractor,
            ))

        return annotations
