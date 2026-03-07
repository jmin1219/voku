"""
"On This Day" resurfacing — surface traces from 1 week / 1 month / 1 quarter ago.

When a new conversation starts, check for meaningful traces at temporal
landmarks. Candidates are included in the first response's system prompt
as natural context — making the AI feel temporally aware without an
explicit notification.

Not stored. Not a notification. Just context that makes the response richer.

Design: TASKS_PHASE7.md § Task 7.5
Anti-collapse: resurface content, not identity claims. "A week ago you
were thinking about..." not "You are someone who..."
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from app.services.storage.sqlite_trace import SQLiteTraceStorage
from app.services.storage.models import Trace


# Temporal windows: (target_days_ago, tolerance_days)
RESURFACE_WINDOWS = [
    (7, 1),    # ~1 week ago ± 1 day
    (30, 2),   # ~1 month ago ± 2 days
    (90, 3),   # ~1 quarter ago ± 3 days
]

MAX_CANDIDATES = 3


@dataclass
class ResurfaceCandidate:
    """A trace worth resurfacing, scored by annotation richness."""
    trace: Trace
    annotation_count: int
    window_label: str  # "~1 week ago", "~1 month ago", "~3 months ago"


class ResurfacingService:
    """Find traces at temporal landmarks for "On This Day" resurfacing."""

    def __init__(self, storage: SQLiteTraceStorage):
        self._storage = storage

    def find_resurface_candidates(
        self,
        current_time: datetime | None = None,
    ) -> list[ResurfaceCandidate]:
        """Find meaningful traces from temporal landmarks.

        Checks 1 week, 1 month, and 1 quarter ago (± tolerance).
        Filters to user traces with annotations. Scores by annotation
        richness. Returns top candidates (max 3).

        Args:
            current_time: Override for testing. Defaults to UTC now.

        Returns:
            List of ResurfaceCandidate, sorted by annotation_count desc.
            Empty list if nothing found.
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        # Collect all user traces with their timestamps
        user_traces = self._get_all_user_traces()
        if not user_traces:
            return []

        candidates: list[ResurfaceCandidate] = []

        for target_days, tolerance, label in [
            (7, 1, "~1 week ago"),
            (30, 2, "~1 month ago"),
            (90, 3, "~3 months ago"),
        ]:
            window_start = current_time - timedelta(days=target_days + tolerance)
            window_end = current_time - timedelta(days=target_days - tolerance)

            window_traces = [
                t for t in user_traces
                if self._trace_in_window(t, window_start, window_end)
            ]

            if not window_traces:
                continue

            # Score by annotation richness and pick the best from this window
            scored = []
            for trace in window_traces:
                annotations = self._storage.get_annotations_for_trace(trace.id)
                if not annotations:
                    continue  # Skip traces with no annotations (empty chatter)
                scored.append(ResurfaceCandidate(
                    trace=trace,
                    annotation_count=len(annotations),
                    window_label=label,
                ))

            if scored:
                # Best from this window
                scored.sort(key=lambda c: c.annotation_count, reverse=True)
                candidates.append(scored[0])

        # Sort all candidates by richness, cap at MAX_CANDIDATES
        candidates.sort(key=lambda c: c.annotation_count, reverse=True)
        return candidates[:MAX_CANDIDATES]

    def format_for_prompt(self, candidates: list[ResurfaceCandidate]) -> str:
        """Format resurface candidates as a system prompt section.

        Returns empty string if no candidates. Otherwise returns a
        natural-language section to append to the system prompt.
        """
        if not candidates:
            return ""

        lines = ["\n## Echoes from your past thinking\n"]

        for c in candidates:
            # Truncate content for prompt budget
            content = c.trace.content[:300]
            if len(c.trace.content) > 300:
                content = content.rsplit(" ", 1)[0] + "…"
            lines.append(f"({c.window_label}) {content}")

        lines.append(
            "\nIf relevant to the current conversation, weave these "
            "naturally — don't force them in. If not relevant, ignore them."
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_all_user_traces(self) -> list[Trace]:
        """Fetch all user traces across all conversations."""
        user_traces: list[Trace] = []
        conversations = self._storage.list_conversations()
        for conv in conversations:
            traces = self._storage.get_traces_by_conversation(conv["id"])
            for t in traces:
                if t.source == "user":
                    user_traces.append(t)
        return user_traces

    @staticmethod
    def _trace_in_window(
        trace: Trace,
        window_start: datetime,
        window_end: datetime,
    ) -> bool:
        """Check if a trace's timestamp falls within the window."""
        try:
            ts = datetime.fromisoformat(trace.timestamp)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return False
        return window_start <= ts <= window_end
