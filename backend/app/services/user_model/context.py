"""
ContextAssemblyV2 — inverse-confidence weighted system prompt.

Piece 4 of Build 4. Completes the vertical slice by wiring user model
intelligence into every conversation. Replaces Build 3's retrieval-only
system prompt with a two-layer design:

  Layer 1: Model state (~300 tokens) — dimension estimates formatted by
           inverse-confidence weighting. Sparse/conflicted dimensions get
           full treatment; stable ones compress to one-liners.

  Layer 2: Retrieved propositions (~400 tokens) — same retrieval as before
           but annotated with which dimension each proposition serves.

Design: USERMODEL.md §4 "Context Assembly — Inverse Confidence Weighting"
"""

from app.services.user_model.storage import UserModelStorage, UserModelRow
from app.services.retrieval import RetrievalService, RetrievalResult
from app.services.embedding.bge import BGEBaseEmbedding


# --- Confidence thresholds ---
STABLE_THRESHOLD = 0.7   # Above this + stable type → one-liner
SPARSE_THRESHOLD = 0.4   # Below this OR sparse type → full treatment


class ContextAssemblyV2:
    """Build context-aware system prompts from user model + retrieval."""

    def __init__(
        self,
        user_model_storage: UserModelStorage,
        retrieval: RetrievalService,
        embedder: BGEBaseEmbedding,
    ):
        self._model = user_model_storage
        self._retrieval = retrieval
        self._embedder = embedder

    def build_system_prompt(
        self, query: str, limit: int = 5
    ) -> tuple[str | None, list[str]]:
        """Build full system prompt: model context + annotated retrievals.

        Returns:
            (system_prompt, retrieval_ids). Prompt is None only if model
            is completely empty AND retrieval returns nothing.
        """
        # Layer 1: Model state
        model_context = self._build_model_context()

        # Layer 2: Retrieved propositions
        results = self._retrieval.retrieve(
            query=query,
            limit=limit,
            temporal_weight=0.3,
            similarity_threshold=0.45,
        )
        retrieval_ids = [r.proposition_id for r in results]
        retrieval_context = self._format_retrievals(results)

        # If both layers empty, no system prompt needed
        if not model_context and not retrieval_context:
            return None, []

        # Assemble final prompt
        sections = [
            "You are Voku, a personal context engine. "
            "You know this person through ongoing conversation."
        ]

        if model_context:
            sections.append(
                f"\n## Your understanding of this person\n\n{model_context}"
            )

        if retrieval_context:
            sections.append(
                f"\n## Relevant context from prior conversations\n\n{retrieval_context}"
            )

        sections.append(
            "\nUse this understanding naturally. Don't list what you know "
            "— weave it into your response as if you already know them.\n"
            "When naturally relevant, create space for the user to elaborate "
            "in areas where your understanding is thin. Don't interrogate."
        )

        return "\n".join(sections), retrieval_ids

    # ------------------------------------------------------------------
    # Layer 1: Model state
    # ------------------------------------------------------------------

    def _build_model_context(self) -> str:
        """Format all active dimensions with inverse-confidence weighting.

        Inverse-confidence is the key idea: dimensions the system understands
        LEAST get the MOST token budget. This naturally focuses the LLM's
        attention on uncertainty — where better conversation can help most.
        """
        dimensions = self._model.get_all_dimensions(status="active")
        if not dimensions:
            return ""

        blocks = [self._format_dimension(dim) for dim in dimensions]
        return "\n\n".join(blocks)

    def _format_dimension(self, dim: UserModelRow) -> str:
        """Format a single dimension. Token budget inversely proportional to confidence.

        Tiers:
          Stable (≥0.7, type=stable):     ~15 tokens — one-liner
          Middle (0.4-0.7, not conflicted): ~40 tokens — estimate + brief note
          Sparse (<0.4 or type=sparse):    ~80 tokens — full treatment
          Conflicted (type=conflicted):    ~80 tokens — full treatment with tension
        """
        label = dim.dimension.replace("_", " ").title()

        # --- Stable: compress to one-liner ---
        if dim.confidence >= STABLE_THRESHOLD and dim.uncertainty_type == "stable":
            return f"**{label}** ({dim.confidence:.0%} confident): {dim.estimate}"

        # --- Conflicted: full treatment, surface the tension ---
        if dim.uncertainty_type == "conflicted":
            parts = [f"**{label}** (conflicted, {dim.confidence:.0%} confident):"]
            if dim.estimate:
                parts.append(dim.estimate)
            if dim.reasoning_trace:
                # Trim reasoning to key tension — avoid dumping entire trace
                tension = _extract_tension(dim.reasoning_trace)
                parts.append(f"Tension: {tension}")
            parts.append(
                "This area shows contradictory signals — explore gently if relevant."
            )
            return "\n".join(parts)

        # --- Sparse: full treatment, highlight unknowns ---
        if dim.confidence < SPARSE_THRESHOLD or dim.uncertainty_type == "sparse":
            parts = [
                f"**{label}** (limited understanding, "
                f"{dim.evidence_count} data points):"
            ]
            if dim.estimate:
                parts.append(dim.estimate)
            else:
                parts.append("No clear picture yet.")
            parts.append(
                "Create space to learn more about this area when naturally relevant."
            )
            return "\n".join(parts)

        # --- Middle ground (0.4–0.7, not conflicted): moderate treatment ---
        parts = [f"**{label}** (developing, {dim.confidence:.0%} confident):"]
        if dim.estimate:
            parts.append(dim.estimate)
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Layer 2: Annotated retrievals
    # ------------------------------------------------------------------

    def _format_retrievals(self, results: list[RetrievalResult]) -> str:
        """Format retrieved propositions with dimension annotations.

        Each proposition is tagged with its primary dimension from
        model_evidence. Unassigned propositions get [uncategorized].
        """
        if not results:
            return ""

        prop_ids = [r.proposition_id for r in results]
        dim_map = self._model.get_primary_dimension_map(prop_ids)

        lines = []
        for r in results:
            dim_label = dim_map.get(r.proposition_id, "uncategorized")
            lines.append(
                f"- [{dim_label}] {r.text} (confidence: {r.confidence:.1f})"
            )

        return "\n".join(lines)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _extract_tension(reasoning_trace: str, max_length: int = 200) -> str:
    """Extract the key tension from a reasoning trace.

    Looks for explicit tension/conflict markers. Falls back to truncation.
    """
    # Look for lines that describe conflict or tension
    for marker in ("tension", "conflict", "contradict", "but ", "however"):
        lower = reasoning_trace.lower()
        idx = lower.find(marker)
        if idx != -1:
            # Take from marker to end of sentence (or max_length)
            snippet = reasoning_trace[idx:]
            # Find sentence boundary
            for end_char in (".", "\n"):
                end = snippet.find(end_char)
                if end != -1 and end < max_length:
                    return snippet[: end + 1].strip()
            return snippet[:max_length].strip()

    # Fallback: just truncate
    if len(reasoning_trace) > max_length:
        return reasoning_trace[:max_length].rstrip() + "…"
    return reasoning_trace
