"""
Temporal digest — AI-synthesized narrative from the trace graph.

"What have I been thinking about this month?" — not a list of traces,
but a narrative that identifies themes, tracks evolution, and notes
contradictions. Summaries are stored as system traces in the graph,
themselves retrievable in future context assembly.

Two operations:
  generate_period_summary(days) → stored system trace with narrative
  get_topic_evolution(query, days) → ephemeral narrative (not stored)

Design: SPEC.md § Build Sequence Phase 7, TASKS_PHASE7.md § Task 7.4
Anti-collapse: narratives use provisional language (~N traces, approximate
timeframes), never identity claims.
"""

import uuid
from datetime import datetime, timezone, timedelta

import numpy as np
from sklearn.cluster import DBSCAN

from app.services.storage.models import Trace, SimilarTrace
from app.services.storage.sqlite_trace import SQLiteTraceStorage
from app.services.embedding.bge import BGEBaseEmbedding
from app.services.providers.base import Provider


def _unwrap_json_narrative(text: str) -> str:
    """Extract plain text from JSON-wrapped LLM responses.

    Some models (e.g. Groq/Llama) ignore 'no JSON' instructions and return
    {"reflection": "..."} or {"narrative": "..."} instead of plain text.
    This strips the wrapper and returns just the text content.
    """
    import json
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            # Try common keys in order of likelihood
            for key in ("reflection", "narrative", "text", "content", "summary"):
                if key in parsed and isinstance(parsed[key], str):
                    return parsed[key].strip()
            # Fallback: join all string values
            values = [v for v in parsed.values() if isinstance(v, str)]
            if values:
                return " ".join(values).strip()
    except (json.JSONDecodeError, TypeError):
        pass
    return text


SUMMARY_PROMPT = """You are writing a temporal digest for a personal thinking environment called Voku.

Given clusters of a person's thinking traces over a time period, write a SHORT narrative synthesis (3-5 paragraphs). This should read like a thoughtful journal reflection, not a report.

Rules:
- Write in second person ("you"). This is addressed to the person whose traces these are.
- Identify themes, evolutions, and contradictions across clusters.
- Reference specific traces by paraphrasing their content — never by IDs.
- Use provisional language: "~N traces suggest...", "over the past weeks...", "there seems to be..."
- Note when thinking evolved or contradicted itself across time.
- Don't list. Narrate.
- Keep it under 400 words.

Respond with ONLY the narrative text. No JSON, no headers, no markdown formatting."""


EVOLUTION_PROMPT = """You are tracing how someone's thinking about a topic evolved over time.

Given their traces in chronological order, write a brief narrative (2-3 paragraphs) showing how their thinking changed. Note shifts, refinements, reversals, and open questions.

Rules:
- Write in second person ("you").
- Reference what they actually said (paraphrase, don't quote IDs).
- Use provisional language.
- If there's no clear evolution (e.g., only one trace), say so honestly.
- Keep it under 250 words.

Respond with ONLY the narrative text."""


class TemporalDigestService:
    """Generate AI-synthesized narratives from the trace graph.

    Period summaries are stored as system traces — retrievable in future
    context assembly. Topic evolutions are ephemeral (on-demand, not stored).
    """

    def __init__(
        self,
        storage: SQLiteTraceStorage,
        embedder: BGEBaseEmbedding,
        provider: Provider,
    ):
        self._storage = storage
        self._embedder = embedder
        self._provider = provider

    async def generate_period_summary(self, days: int = 30) -> Trace:
        """Generate and store a narrative summary for a time period.

        Args:
            days: Lookback window in days.

        Returns:
            The system trace containing the narrative.

        Raises:
            ValueError: If no user traces exist in the window.
            RuntimeError: If LLM generation fails.
        """
        traces = self._get_traces_in_window(days)
        user_traces = [t for t in traces if t.source == "user"]

        if not user_traces:
            raise ValueError(
                f"No user traces found in the last {days} days. "
                "Keep using Voku — the digest becomes meaningful with accumulated thinking."
            )

        # Cluster user traces for thematic grouping
        clustered = self._cluster_traces(user_traces)

        # Build LLM prompt with clustered content
        prompt = self._build_summary_prompt(clustered, days)

        try:
            narrative = await self._provider.complete(
                prompt,
                system_prompt=SUMMARY_PROMPT,
                max_tokens=1024,
            )
        except Exception as e:
            raise RuntimeError(f"Digest generation failed: {e}") from e

        narrative = narrative.strip()
        if not narrative:
            raise RuntimeError("LLM returned empty narrative")

        # Unwrap JSON if LLM ignored "no JSON" instruction (common with Groq)
        narrative = _unwrap_json_narrative(narrative)

        # Store as system trace
        now = datetime.now(timezone.utc)
        date_label = now.strftime("%Y-%m-%d")

        digest_trace = Trace(
            id=str(uuid.uuid4()),
            timestamp=now.isoformat(),
            content=narrative,
            conversation_id=f"digest-{date_label}",
            parent_trace_id=None,
            source="system",
        )
        self._storage.store_trace(digest_trace)

        # Embed so future context assembly can retrieve it
        embedding = self._embedder.embed(narrative)
        self._storage.store_embedding(
            digest_trace.id, embedding, self._embedder.model_name
        )

        return digest_trace

    async def get_topic_evolution(self, query: str, days: int = 60) -> str:
        """Trace how thinking about a topic evolved over time.

        On-demand, not stored. Returns the narrative string directly.

        Args:
            query: Topic to trace (e.g., "career direction", "training").
            days: Lookback window in days.

        Returns:
            Narrative string describing the evolution.

        Raises:
            ValueError: If no relevant traces found.
            RuntimeError: If LLM generation fails.
        """
        query_embedding = self._embedder.embed(query)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Find semantically similar traces
        similar = self._storage.find_similar(
            query_embedding,
            threshold=0.35,
            limit=30,
        )

        # Filter to user traces within time window
        relevant = [
            s for s in similar
            if s.trace.source == "user" and s.trace.timestamp >= cutoff
        ]

        if not relevant:
            raise ValueError(
                f"No traces about '{query}' found in the last {days} days."
            )

        # Sort chronologically
        relevant.sort(key=lambda s: s.trace.timestamp)

        # Build prompt
        prompt = self._build_evolution_prompt(relevant, query, days)

        try:
            narrative = await self._provider.complete(
                prompt,
                system_prompt=EVOLUTION_PROMPT,
                max_tokens=512,
            )
        except Exception as e:
            raise RuntimeError(f"Evolution narrative failed: {e}") from e

        narrative = narrative.strip()
        if not narrative:
            raise RuntimeError("LLM returned empty evolution narrative")

        narrative = _unwrap_json_narrative(narrative)
        return narrative

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_traces_in_window(self, days: int) -> list[Trace]:
        """Fetch all traces within the time window.

        Iterates conversations since SQLiteTraceStorage doesn't have
        a direct time-range query. Acceptable at <10K traces.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        traces_in_window: list[Trace] = []

        conversations = self._storage.list_conversations()
        for conv in conversations:
            traces = self._storage.get_traces_by_conversation(conv["id"])
            for t in traces:
                if t.timestamp >= cutoff:
                    traces_in_window.append(t)

        # Also check system traces with no conversation_id (e.g., prior digests)
        # These won't appear in list_conversations() since it filters NULL conversation_ids
        # For now, conversation-grouped traces cover the main use case.

        return traces_in_window

    def _cluster_traces(
        self, traces: list[Trace]
    ) -> list[dict]:
        """Cluster traces by embedding similarity for thematic grouping.

        Returns list of {"label": int, "traces": [Trace, ...]}.
        Unclustered traces (label=-1) grouped as "miscellaneous".
        """
        if len(traces) < 3:
            # Too few to cluster — return all as one group
            return [{"label": 0, "traces": traces}]

        # Get embeddings from cache
        all_ids, all_matrix = self._storage.get_all_embeddings()
        id_to_idx = {tid: i for i, tid in enumerate(all_ids)}

        # Build aligned vectors for traces we have embeddings for
        valid_traces = []
        vectors = []
        for t in traces:
            if t.id in id_to_idx:
                valid_traces.append(t)
                vectors.append(all_matrix[id_to_idx[t.id]])

        if len(valid_traces) < 3:
            return [{"label": 0, "traces": traces}]

        X = np.array(vectors)
        norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-10
        X_normed = X / norms

        # DBSCAN with cosine distance — same params as trace_projection
        db = DBSCAN(eps=0.3, min_samples=2, metric="cosine").fit(X_normed)
        labels = db.labels_

        # Group by cluster label
        groups: dict[int, list[Trace]] = {}
        for i, trace in enumerate(valid_traces):
            label = int(labels[i])
            groups.setdefault(label, []).append(trace)

        result = []
        for label in sorted(groups.keys()):
            result.append({"label": label, "traces": groups[label]})

        return result

    def _build_summary_prompt(
        self, clustered: list[dict], days: int
    ) -> str:
        """Build the user prompt for period summary generation."""
        lines = [f"Time period: last {days} days\n"]

        for group in clustered:
            label = group["label"]
            traces = group["traces"]

            if label == -1:
                lines.append(f"--- Miscellaneous (~{len(traces)} traces) ---")
            else:
                lines.append(f"--- Cluster {label} (~{len(traces)} traces) ---")

            # Sort chronologically within cluster
            sorted_traces = sorted(traces, key=lambda t: t.timestamp)

            # Include up to 8 representative traces per cluster
            for t in sorted_traces[:8]:
                try:
                    ts = datetime.fromisoformat(t.timestamp)
                    date_str = ts.strftime("%b %d")
                except (ValueError, TypeError):
                    date_str = "?"
                content = t.content[:300]
                lines.append(f"  [{date_str}] {content}")

            if len(sorted_traces) > 8:
                lines.append(f"  ... and {len(sorted_traces) - 8} more traces")

            lines.append("")

        return "\n".join(lines)

    def _build_evolution_prompt(
        self, similar: list[SimilarTrace], query: str, days: int
    ) -> str:
        """Build the user prompt for topic evolution narrative."""
        lines = [
            f"Topic: {query}",
            f"Time period: last {days} days",
            f"Traces (chronological, {len(similar)} total):\n",
        ]

        for s in similar[:15]:  # Cap at 15 for token budget
            try:
                ts = datetime.fromisoformat(s.trace.timestamp)
                date_str = ts.strftime("%b %d, %H:%M")
            except (ValueError, TypeError):
                date_str = "?"
            content = s.trace.content[:250]
            lines.append(f"  [{date_str}] {content}")

        if len(similar) > 15:
            lines.append(f"  ... and {len(similar) - 15} more traces")

        return "\n".join(lines)
