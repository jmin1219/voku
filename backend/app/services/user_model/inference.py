"""
ExhaleService — per-dimension inference over accumulated evidence.

Piece 3 of Build 4. The "exhale" in the breathing architecture:
propositions (evidence) accumulated during conversations are periodically
synthesized into dimension-level beliefs (estimates).

Each dimension gets a focused LLM call with its evidence, current state,
and active goals. A threshold gate prevents LLM stochasticity from
polluting summary_history — only genuine belief shifts get recorded.

Gate conditions (ALL must pass to record a change):
  1. Semantic delta: cosine(old_embedding, new_embedding) < 0.9
  2. Confidence delta: |old_confidence - new_confidence| > 0.1
  3. Evidence citation: reasoning_trace references specific proposition IDs
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from app.services.embedding.bge import BGEBaseEmbedding
from app.services.providers.base import Provider, ProviderError
from app.services.user_model.storage import UserModelStorage, UserModelRow


@dataclass
class ExhaleResult:
    """Result of running exhale on one dimension."""
    dimension_id: str
    old_estimate: str
    new_estimate: str
    old_confidence: float
    new_confidence: float
    uncertainty_type: str         # sparse | conflicted | stable
    reasoning_trace: str
    gate_passed: bool
    gate_reason: str | None       # why it failed, if it did
    evidence_count: int
    goal_ids: list[str]


@dataclass
class ExhaleAllResult:
    """Result of running exhale on all eligible dimensions."""
    results: list[ExhaleResult]
    updated: int                  # dimensions where gate passed and DB was updated
    skipped: int                  # gate failed
    errors: int


# --- Threshold gate constants ---
SEMANTIC_SIMILARITY_THRESHOLD = 0.9   # cosine sim above this = "same thing, different words"
CONFIDENCE_DELTA_THRESHOLD = 0.1      # minimum change to count as meaningful


SYSTEM_PROMPT = """You are synthesizing evidence about one aspect of a person's life into a coherent understanding.

You will receive:
- A dimension name and description (what aspect of this person's life you're assessing)
- The current estimate (what the system currently believes — may be empty for first run)
- All evidence: propositions extracted from conversations, with relevance scores and direction

Your job:
1. Read ALL evidence carefully. Weight higher-relevance propositions more heavily.
2. Note contradictions — propositions marked "contradicts" or evidence that conflicts.
3. Note retrospective evidence — if someone recounts history, that tells you about the past AND about what's psychologically active for them now.
4. Synthesize into a natural-language ESTIMATE of this dimension. Write as if describing this aspect of the person to someone who will have a conversation with them. Be specific, cite patterns, note tensions.
5. Assess CONFIDENCE (0.0-1.0): how well do you understand this dimension? 0.0 = no real signal. 0.5 = reasonable picture with gaps. 0.8+ = strong consistent evidence.
6. Classify UNCERTAINTY TYPE:
   - "sparse": few evidence points, picture is incomplete
   - "conflicted": evidence disagrees or person seems in transition
   - "stable": consistent evidence, reliable understanding
7. In reasoning_trace, reference SPECIFIC proposition IDs that drove your assessment. This is required.

Respond with valid JSON only. No markdown fences."""


def _build_exhale_prompt(
    dimension: UserModelRow,
    evidence: list[dict],
    active_goals: list[dict],
) -> str:
    """Build the user prompt for exhaling one dimension."""

    # Format evidence
    evidence_lines = []
    for i, e in enumerate(evidence):
        direction_tag = ""
        if e["direction"] == "contradicts":
            direction_tag = " ⚡CONTRADICTS"
        elif e["direction"] == "contextualizes":
            direction_tag = " ↩contextualizes"

        mode_tag = ""
        if e.get("evidence_mode") == "retrospective":
            mode_tag = " [retrospective]"

        evidence_lines.append(
            f'{i+1}. [{e["proposition_id"]}] (relevance: {e["relevance"]:.2f}{direction_tag}{mode_tag}) '
            f'({e["node_type"]}) "{e["text"]}"'
        )
    evidence_block = "\n".join(evidence_lines) if evidence_lines else "(no evidence yet)"

    # Format goals
    goal_block = ""
    if active_goals:
        goal_lines = [f'- [{g["id"]}] "{g["text"]}"' for g in active_goals]
        goal_block = f"\n\n## Active Goals (intention-type, high confidence)\n\n" + "\n".join(goal_lines)
        goal_block += "\n\nNote which goals connect to this dimension's evidence."

    # Current state
    current = dimension.estimate or "(first assessment — no prior estimate)"
    current_conf = dimension.confidence

    return f"""## Dimension: {dimension.dimension}

**Description:** {dimension.description}

**Current estimate:** {current}
**Current confidence:** {current_conf}
**Evidence count:** {len(evidence)}{goal_block}

## Evidence (ordered by time, oldest first)

{evidence_block}

## Response format

Return a JSON object:
{{
  "estimate": "Your natural-language assessment of this dimension (2-5 sentences, specific and grounded in evidence)",
  "confidence": 0.0-1.0,
  "uncertainty_type": "sparse" or "conflicted" or "stable",
  "reasoning_trace": "Which proposition IDs drove this assessment and why. Note any contradictions, retrospective evidence patterns, or goal connections.",
  "goal_ids": ["list", "of", "active goal IDs connected to this dimension"]
}}"""


def _parse_exhale_response(raw: str) -> dict | None:
    """Parse LLM response into exhale fields. Returns None on failure."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    estimate = data.get("estimate")
    if not estimate or not isinstance(estimate, str):
        return None

    confidence = data.get("confidence", 0.5)
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.5

    uncertainty_type = data.get("uncertainty_type", "sparse")
    if uncertainty_type not in ("sparse", "conflicted", "stable"):
        uncertainty_type = "sparse"

    reasoning_trace = data.get("reasoning_trace", "")
    if not isinstance(reasoning_trace, str):
        reasoning_trace = str(reasoning_trace)

    goal_ids = data.get("goal_ids", [])
    if not isinstance(goal_ids, list):
        goal_ids = []
    goal_ids = [g for g in goal_ids if isinstance(g, str)]

    return {
        "estimate": estimate,
        "confidence": round(confidence, 2),
        "uncertainty_type": uncertainty_type,
        "reasoning_trace": reasoning_trace,
        "goal_ids": goal_ids,
    }


def _check_citation(reasoning_trace: str, evidence: list[dict]) -> bool:
    """Verify reasoning_trace references at least one proposition ID from the evidence."""
    if not reasoning_trace or not evidence:
        return False
    evidence_ids = {e["proposition_id"] for e in evidence}
    # Look for any evidence ID substring in the trace
    for eid in evidence_ids:
        if eid in reasoning_trace:
            return True
        # Also check short form (first 8 chars of UUID)
        if eid[:8] in reasoning_trace:
            return True
    return False


class ExhaleService:
    """Per-dimension inference over accumulated evidence."""

    def __init__(
        self,
        storage: UserModelStorage,
        embedder: BGEBaseEmbedding,
        provider: Provider,
    ):
        self.storage = storage
        self.embedder = embedder
        self.provider = provider

    def _threshold_gate(
        self,
        old_estimate: str,
        new_estimate: str,
        old_confidence: float,
        new_confidence: float,
        reasoning_trace: str,
        evidence: list[dict],
    ) -> tuple[bool, str | None]:
        """Check whether the change is meaningful enough to record.

        Returns (passed, reason_if_failed).
        """
        # First exhale: no old estimate to compare against — always pass
        if not old_estimate:
            return True, None

        # Gate 1: semantic delta
        old_emb = self.embedder.embed(old_estimate)
        new_emb = self.embedder.embed(new_estimate)
        similarity = float(np.dot(old_emb, new_emb))  # normalized vectors → dot = cosine
        if similarity > SEMANTIC_SIMILARITY_THRESHOLD:
            return False, f"semantic_delta_too_small (cosine={similarity:.3f})"

        # Gate 2: confidence delta
        conf_delta = abs(new_confidence - old_confidence)
        if conf_delta < CONFIDENCE_DELTA_THRESHOLD:
            # Relaxed: if semantic delta is large, confidence doesn't need to change
            if similarity > 0.85:
                return False, f"confidence_delta_too_small ({conf_delta:.2f}) and semantic barely changed"

        # Gate 3: evidence citation
        if not _check_citation(reasoning_trace, evidence):
            return False, "no_evidence_citation_in_reasoning_trace"

        return True, None

    async def exhale(self, dimension_id: str) -> ExhaleResult:
        """Run inference on one dimension.

        Gathers evidence, calls LLM, applies threshold gate,
        commits if gate passes.
        """
        # 1. Load dimension
        dimension = self.storage.get_dimension(dimension_id)
        if not dimension:
            raise ValueError(f"Dimension {dimension_id} not found")

        # 2. Gather evidence
        evidence = self.storage.get_evidence_for_dimension(dimension_id)

        # 3. Find active goals (intention-type props with confidence >= 0.7)
        # Query propositions directly — goals are high-confidence intentions
        import sqlite3
        conn = sqlite3.connect(self.storage.db_path)
        conn.row_factory = sqlite3.Row
        goal_rows = conn.execute(
            """SELECT id, text, confidence FROM propositions
               WHERE node_type = 'intention' AND confidence >= 0.7
               AND status = 'active'
               ORDER BY created_at DESC LIMIT 10"""
        ).fetchall()
        conn.close()
        active_goals = [{"id": r["id"], "text": r["text"]} for r in goal_rows]

        # 4. Build prompt and call LLM
        prompt = _build_exhale_prompt(dimension, evidence, active_goals)

        try:
            raw = await self.provider.complete(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                max_tokens=1024,
            )
        except ProviderError as e:
            return ExhaleResult(
                dimension_id=dimension_id,
                old_estimate=dimension.estimate,
                new_estimate="",
                old_confidence=dimension.confidence,
                new_confidence=dimension.confidence,
                uncertainty_type=dimension.uncertainty_type,
                reasoning_trace=f"LLM call failed: {e}",
                gate_passed=False,
                gate_reason="llm_error",
                evidence_count=len(evidence),
                goal_ids=[],
            )

        # 5. Parse response
        parsed = _parse_exhale_response(raw)
        if not parsed:
            return ExhaleResult(
                dimension_id=dimension_id,
                old_estimate=dimension.estimate,
                new_estimate="",
                old_confidence=dimension.confidence,
                new_confidence=dimension.confidence,
                uncertainty_type=dimension.uncertainty_type,
                reasoning_trace=f"Parse failed. Raw: {raw[:200]}",
                gate_passed=False,
                gate_reason="parse_error",
                evidence_count=len(evidence),
                goal_ids=[],
            )

        # 6. Threshold gate
        gate_passed, gate_reason = self._threshold_gate(
            old_estimate=dimension.estimate,
            new_estimate=parsed["estimate"],
            old_confidence=dimension.confidence,
            new_confidence=parsed["confidence"],
            reasoning_trace=parsed["reasoning_trace"],
            evidence=evidence,
        )

        # 7. Commit if gate passes
        if gate_passed:
            # Append old estimate to history before overwriting
            if dimension.estimate:
                now = datetime.now(timezone.utc).isoformat()
                self.storage.append_history(
                    dimension_id,
                    dimension.estimate,
                    dimension.confidence,
                    now,
                )

            self.storage.update_dimension(
                dim_id=dimension_id,
                estimate=parsed["estimate"],
                confidence=parsed["confidence"],
                uncertainty_type=parsed["uncertainty_type"],
                reasoning_trace=parsed["reasoning_trace"],
                evidence_count=len(evidence),
            )

            # Update goal_relevance
            if parsed["goal_ids"]:
                import sqlite3 as _sqlite3
                _conn = _sqlite3.connect(self.storage.db_path)
                _conn.execute(
                    "UPDATE user_model SET goal_relevance = ? WHERE id = ?",
                    (json.dumps(parsed["goal_ids"]), dimension_id),
                )
                _conn.commit()
                _conn.close()

        result = ExhaleResult(
            dimension_id=dimension_id,
            old_estimate=dimension.estimate,
            new_estimate=parsed["estimate"],
            old_confidence=dimension.confidence,
            new_confidence=parsed["confidence"],
            uncertainty_type=parsed["uncertainty_type"],
            reasoning_trace=parsed["reasoning_trace"],
            gate_passed=gate_passed,
            gate_reason=gate_reason,
            evidence_count=len(evidence),
            goal_ids=parsed["goal_ids"],
        )

        return result

    async def exhale_all(self) -> ExhaleAllResult:
        """Run exhale on all active dimensions with evidence.

        Skips dimensions with 0 evidence (nothing to synthesize).
        """
        dimensions = self.storage.get_all_dimensions(status="active")
        results: list[ExhaleResult] = []
        updated = 0
        skipped = 0
        errors = 0

        for dim in dimensions:
            evidence = self.storage.get_evidence_for_dimension(dim.id)
            if not evidence:
                print(f"  {dim.id}: 0 evidence, skipping")
                skipped += 1
                continue

            print(f"  {dim.id}: {len(evidence)} evidence points, exhaling...")
            result = await self.exhale(dim.id)
            results.append(result)

            if result.gate_reason in ("llm_error", "parse_error"):
                errors += 1
                print(f"    ❌ {result.gate_reason}")
            elif result.gate_passed:
                updated += 1
                print(f"    ✅ Updated: confidence {result.old_confidence:.2f} → {result.new_confidence:.2f}")
            else:
                skipped += 1
                print(f"    ⏭ Gate failed: {result.gate_reason}")

        return ExhaleAllResult(
            results=results,
            updated=updated,
            skipped=skipped,
            errors=errors,
        )
