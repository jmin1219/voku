"""
Trace-based context assembly — format retrieved traces into LLM system prompt.

v2 replacement for ContextAssemblyV2. Simpler: no user model layer,
no dimension assignments, no inverse-confidence weighting. The system
prompt is assembled directly from retrieved traces.

Returns (system_prompt, trace_ids) so the chat route can:
  1. Pass the prompt to the LLM
  2. Emit trace_ids as an SSE event for frontend context markers

Design: SPEC.md § Context Assembly
Constraint 0.1: Conversation quality must improve with accumulated context.
"""

from datetime import datetime, timezone

from app.services.trace_retrieval import TraceRetrievalService, TraceRetrievalResult
from app.services.contradiction import ContradictionDetector


# --- Token budget ---
# SPEC says ~500-800 tokens for retrieval context.
# At ~4 chars/token, that's ~2000-3200 chars total.
# With 5 traces, each gets ~400-640 chars.
MAX_TRACE_CHARS = 500


class TraceContextAssembly:
    """Build context-aware system prompts from retrieved traces.

    No user model. No dimensions. The trace graph IS the understanding.
    """

    def __init__(self, retrieval: TraceRetrievalService, contradiction_detector: ContradictionDetector | None = None):
        self._retrieval = retrieval
        self._contradiction = contradiction_detector

    def build_system_prompt(
        self, query: str, limit: int = 5
    ) -> tuple[str | None, list[str]]:
        """Build system prompt from retrieved traces.

        Args:
            query: The user's current message.
            limit: Max traces to retrieve and include.

        Returns:
            (system_prompt, trace_ids). Prompt is None if no traces found.
            trace_ids ordered by combined score (same order as in prompt).
        """
        results = self._retrieval.retrieve(
            query=query,
            limit=limit,
            temporal_weight=0.3,
            similarity_threshold=0.45,
        )

        if not results:
            today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
            return (
                f"You are Voku, a personal thinking environment. Today is {today}. "
                "You know this person through ongoing conversation. "
                "No prior context yet — this is early in the relationship."
            ), []

        trace_ids = [r.trace.id for r in results]
        retrieval_block = self._format_traces(results)

        # Detect contradictions if detector is available
        contradiction_cue = ""
        if self._contradiction and len(results) >= 2:
            contradictions = self._contradiction.detect(results)
            if contradictions:
                pairs = []
                for earlier_id, later_id in contradictions:
                    earlier_idx = next(
                        (i + 1 for i, r in enumerate(results) if r.trace.id == earlier_id), None
                    )
                    later_idx = next(
                        (i + 1 for i, r in enumerate(results) if r.trace.id == later_id), None
                    )
                    if earlier_idx and later_idx:
                        pairs.append(f"[{earlier_idx}] and [{later_idx}]")
                if pairs:
                    contradiction_cue = (
                        f"\nNote: traces {', '.join(pairs)} address the same topic but "
                        "reflect different positions taken at different times. "
                        "Present this as evolution, not confusion."
                    )

        today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
        prompt = (
            "You are Voku, a personal thinking environment. "
            f"Today is {today}. "
            "You know this person through ongoing conversation.\n"
            "\n## Relevant context from prior conversations\n\n"
            f"{retrieval_block}\n"
            "\nUse this context naturally. Don't list what you know "
            "— weave it into your response as if you already know them.\n"
            "Reference numbers like [1] correspond to specific past moments "
            "— the user can see which parts of their history you drew from."
            f"{contradiction_cue}"
        )

        return prompt, trace_ids

    def _format_traces(self, results: list[TraceRetrievalResult]) -> str:
        """Format retrieved traces for the system prompt.

        Each trace gets an index number [1], [2], etc. for context markers,
        a relative timestamp, source label, and content (truncated if needed).
        """
        now = datetime.now(timezone.utc)
        lines = []

        for i, result in enumerate(results, start=1):
            trace = result.trace
            source_label = _source_label(trace.source)
            time_label = _relative_time(trace.timestamp, now)
            content = _truncate(trace.content, MAX_TRACE_CHARS)
            lines.append(f"[{i}] ({source_label}, {time_label}): {content}")

        return "\n".join(lines)


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------


def _source_label(source: str) -> str:
    """Human-readable source label for the system prompt."""
    labels = {
        "user": "you",
        "assistant": "assistant",
        "resource": "resource",
        "system": "system",
    }
    return labels.get(source, source)


def _relative_time(timestamp: str, now: datetime) -> str:
    """Convert ISO timestamp to human-readable relative time.

    Examples: 'just now', '2 hours ago', '3 days ago', '2 weeks ago', '1 month ago'
    """
    try:
        created = datetime.fromisoformat(timestamp)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return "unknown time"

    delta = now - created
    seconds = delta.total_seconds()

    if seconds < 0:
        return "just now"
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    if seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    months = int(seconds / 2592000)
    return f"{months} month{'s' if months != 1 else ''} ago"


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars at a sentence boundary if possible."""
    if len(text) <= max_chars:
        return text

    # Try to cut at last sentence boundary before max_chars
    truncated = text[:max_chars]
    for end_char in (". ", "! ", "? ", ".\n", "!\n", "?\n"):
        last = truncated.rfind(end_char)
        if last > max_chars * 0.5:  # Don't cut too aggressively
            return truncated[: last + 1].rstrip()

    # Fallback: cut at last space
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.5:
        return truncated[:last_space] + "…"

    return truncated + "…"
