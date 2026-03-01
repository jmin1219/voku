"""
Contradiction detection — find opposing traces in retrieval results.

When two retrieved traces address the same topic but express opposing
positions (same annotation key, different values), flag them for the
LLM to present as evolution rather than confusion.

Design: SPEC.md § UI/UX Architecture — Contradiction Surfacing
Anti-collapse principle: contradictions coexist, never forced resolution.
"""

from app.services.storage.sqlite_trace import SQLiteTraceStorage
from app.services.trace_retrieval import TraceRetrievalResult


class ContradictionDetector:
    """Detect contradictory trace pairs in retrieval results.

    Strategy: Among retrieved traces, find pairs where annotations share
    the same (type, key) but have different values. This catches cases
    like "decided to focus on rowing" vs "dropped the rowing goal".
    """

    def __init__(self, storage: SQLiteTraceStorage):
        self._storage = storage

    def detect(
        self, results: list[TraceRetrievalResult]
    ) -> list[tuple[str, str]]:
        """Find contradictory trace pairs.

        Args:
            results: Retrieved traces from the retrieval pipeline.

        Returns:
            List of (earlier_trace_id, later_trace_id) pairs ordered
            chronologically. Empty if no contradictions found.
        """
        if len(results) < 2:
            return []

        # Build annotation index: {(type, key): [(trace_id, value, timestamp)]}
        ann_index: dict[tuple[str, str], list[tuple[str, str, str]]] = {}

        for r in results:
            annotations = self._storage.get_annotations_for_trace(r.trace.id)
            for ann in annotations:
                if ann.key is None:
                    continue
                group_key = (ann.type, ann.key)
                entry = (r.trace.id, ann.value or "", r.trace.timestamp)
                ann_index.setdefault(group_key, []).append(entry)

        # Find pairs with same (type, key) but different values
        contradictions: list[tuple[str, str]] = []
        seen_pairs: set[frozenset[str]] = set()

        for group_key, entries in ann_index.items():
            if len(entries) < 2:
                continue

            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    tid_a, val_a, ts_a = entries[i]
                    tid_b, val_b, ts_b = entries[j]

                    if tid_a == tid_b:
                        continue
                    if val_a == val_b:
                        continue  # Same value = consistent, not contradictory

                    pair = frozenset({tid_a, tid_b})
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)

                    # Order chronologically
                    if ts_a <= ts_b:
                        contradictions.append((tid_a, tid_b))
                    else:
                        contradictions.append((tid_b, tid_a))

        return contradictions
