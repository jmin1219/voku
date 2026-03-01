"""
Pattern detection — surface recurring annotation tendencies.

Scans annotations within a timeframe to find recurring patterns.
Patterns are computed, not stored. Cached per session.

Design: SPEC.md § UI/UX Architecture — Pattern-Opinions
Anti-collapse: descriptions use provisional language, scoped to
timeframe, grounded in specific traces.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from app.services.storage.sqlite_trace import SQLiteTraceStorage


@dataclass
class Pattern:
    """A detected recurring tendency in the user's traces."""
    type: str                         # 'frequency' | 'unmet_commitment' | 'recurring_topic'
    description: str                  # Provisional language, always
    trace_ids: list[str] = field(default_factory=list)
    timeframe: str = ""               # e.g. "last 2 weeks"
    confidence: float = 0.5


class PatternService:
    """Detect annotation patterns within a timeframe."""

    def __init__(self, storage: SQLiteTraceStorage):
        self._storage = storage

    def detect_patterns(
        self,
        days: int = 14,
        min_occurrences: int = 3,
    ) -> list[Pattern]:
        """Find recurring annotation patterns within the last `days` days.

        Args:
            days: Lookback window in days.
            min_occurrences: Minimum annotations with same (type, key) to trigger.

        Returns:
            List of Pattern objects, sorted by occurrence count descending.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Group annotations by (type, key) within timeframe
        # Need to join annotations with traces to filter by trace timestamp
        groups: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
        # groups[(ann_type, ann_key)] = [(trace_id, trace_timestamp), ...]

        # Get all traces within timeframe
        # No direct query for this — iterate conversations
        conversations = self._storage.list_conversations()
        trace_ids_in_window: set[str] = set()

        for conv in conversations:
            traces = self._storage.get_traces_by_conversation(conv["id"])
            for t in traces:
                if t.timestamp >= cutoff:
                    trace_ids_in_window.add(t.id)

        if not trace_ids_in_window:
            return []

        # Collect annotations for traces in window
        for trace_id in trace_ids_in_window:
            annotations = self._storage.get_annotations_for_trace(trace_id)
            for ann in annotations:
                if ann.key is None:
                    continue
                group_key = (ann.type, ann.key)
                groups[group_key].append((trace_id, ann.value or ""))

        # Find groups meeting threshold
        patterns = []
        timeframe_label = f"last {days} days" if days != 7 else "last week"

        for (ann_type, ann_key), entries in groups.items():
            if len(entries) < min_occurrences:
                continue

            trace_ids = list(dict.fromkeys(tid for tid, _ in entries))  # dedupe, preserve order
            count = len(entries)

            # Provisional language
            description = f"~{count} {ann_type}s about {ann_key} in the {timeframe_label}"

            patterns.append(Pattern(
                type="frequency",
                description=description,
                trace_ids=trace_ids,
                timeframe=timeframe_label,
                confidence=min(0.9, 0.5 + count * 0.1),
            ))

        # Sort by count descending
        patterns.sort(key=lambda p: len(p.trace_ids), reverse=True)
        return patterns
