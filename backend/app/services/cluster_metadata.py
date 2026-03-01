"""
Cluster metadata generation — LLM labels + summaries for trace clusters.

For each cluster, selects the top-5 most central traces (closest to
centroid in embedding space) and asks the LLM for a 3-5 word label
and one-sentence summary. Falls back to keyword extraction when
LLM is unavailable or the cluster is too small.

Design: SPEC.md § UI/UX Architecture — Cloud Level
Anti-collapse: labels use tilde (~47 traces about...), never identity claims.
"""

import json
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from app.services.storage.models import Trace
from app.services.providers.base import Provider


LABEL_PROMPT = """You are generating a label and summary for a cluster of conversational traces in a personal knowledge system.

Given the most central traces from this cluster, produce:
- "label": A 3-5 word topic label (lowercase, no articles)
- "summary": One sentence describing what these traces are about

Respond with ONLY a JSON object. No other text. Example:
{"label": "career direction exploration", "summary": "Traces exploring career options and decisions about professional direction."}"""


STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "has",
    "been", "was", "were", "are", "but", "not", "they", "their", "than",
    "its", "also", "about", "into", "more", "when", "what", "which",
    "will", "would", "could", "should", "does", "did", "had", "being",
    "over", "after", "before", "between", "through", "during", "without",
    "because", "each", "other", "some", "very", "just", "only", "then",
    "still", "even", "most", "much", "both", "same", "such", "like",
    "used", "using", "based", "need", "want", "make", "take", "user",
    "keep", "trace", "traces", "cluster", "about",
}


@dataclass
class ClusterMeta:
    """Metadata for a single cluster."""
    cluster_id: int
    label: str
    summary: str
    central_trace_ids: list[str] = field(default_factory=list)


class ClusterMetadataService:
    """Generate labels and summaries for trace clusters."""

    def __init__(self, provider: Provider):
        self._provider = provider

    async def generate_labels(
        self,
        clusters: list[dict],
        traces: list[Trace],
        embeddings: dict[str, np.ndarray],
    ) -> list[ClusterMeta]:
        """Generate label + summary for each cluster.

        Args:
            clusters: List of {"id": int, "trace_ids": [str, ...]}
            traces: All traces (for content lookup).
            embeddings: {trace_id: embedding_vector}

        Returns:
            List of ClusterMeta, one per cluster.
        """
        if not clusters:
            return []

        traces_by_id = {t.id: t for t in traces}
        results = []

        for cluster in clusters:
            cid = cluster["id"]
            trace_ids = cluster["trace_ids"]

            # Find central traces
            central_ids = self._find_central_traces(trace_ids, embeddings, k=5)
            central_traces = [
                traces_by_id[tid] for tid in central_ids
                if tid in traces_by_id
            ]

            if len(central_traces) < 3:
                # Too small for LLM — keyword fallback
                label = self._keyword_label(central_traces)
                results.append(ClusterMeta(
                    cluster_id=cid,
                    label=label,
                    summary="",
                    central_trace_ids=central_ids,
                ))
                continue

            # Try LLM
            try:
                label, summary = await self._llm_label(central_traces)
                results.append(ClusterMeta(
                    cluster_id=cid,
                    label=label,
                    summary=summary,
                    central_trace_ids=central_ids,
                ))
            except Exception:
                # LLM failed — keyword fallback
                label = self._keyword_label(central_traces)
                results.append(ClusterMeta(
                    cluster_id=cid,
                    label=label,
                    summary="",
                    central_trace_ids=central_ids,
                ))

        return results

    def _find_central_traces(
        self,
        trace_ids: list[str],
        embeddings: dict[str, np.ndarray],
        k: int = 5,
    ) -> list[str]:
        """Find k traces closest to the cluster centroid in embedding space."""
        vecs = []
        valid_ids = []
        for tid in trace_ids:
            if tid in embeddings:
                vecs.append(embeddings[tid])
                valid_ids.append(tid)

        if not vecs:
            return trace_ids[:k]

        matrix = np.array(vecs)
        centroid = matrix.mean(axis=0)

        # Cosine distance to centroid
        centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-10)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
        normalized = matrix / norms
        similarities = normalized @ centroid_norm

        # Top k by similarity (closest to centroid)
        k_eff = min(k, len(valid_ids))
        top_indices = np.argsort(similarities)[::-1][:k_eff]
        return [valid_ids[i] for i in top_indices]

    async def _llm_label(self, traces: list[Trace]) -> tuple[str, str]:
        """Ask LLM for label + summary from central traces."""
        content_block = "\n".join(
            f"- {t.content[:200]}" for t in traces
        )
        prompt = f"Central traces from this cluster:\n{content_block}"

        response = await self._provider.complete(
            prompt,
            system_prompt=LABEL_PROMPT,
            max_tokens=256,
        )

        # Parse JSON response
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        data = json.loads(text)
        label = data.get("label", "unlabeled cluster")
        summary = data.get("summary", "")
        return label, summary

    def _keyword_label(self, traces: list[Trace]) -> str:
        """Fallback: extract top keywords from trace content."""
        word_counts: Counter = Counter()
        for t in traces:
            words = t.content.lower().split()
            for w in words:
                w = w.strip(".,;:!?()\"'")
                if len(w) > 3 and w not in STOPWORDS:
                    word_counts[w] += 1

        top = [w for w, _ in word_counts.most_common(3)]
        return " / ".join(top) if top else "uncategorized"
