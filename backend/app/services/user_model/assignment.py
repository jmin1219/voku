"""
AssignmentService — classify propositions into user model dimensions.

Piece 2 of Build 4. Two-pass design:
  Pass 1 (this piece): Which dimensions does this proposition inform? (0-3 per prop)
  Pass 2 (Piece 2b):   How? Relevance score + direction per assignment.

With 4 coarse seed dimensions, Pass 1 is trivially easy for the LLM.
The prompt asks "what does this tell you about this person?" — framing
as inference, not categorization.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.providers.base import Provider, ProviderError
from app.services.user_model.storage import UserModelRow, EvidenceRow


@dataclass
class AssignmentResult:
    """Result of classifying one proposition."""
    proposition_id: str
    dimension_ids: list[str]  # 0-3 dimension IDs
    evidence_mode: str        # experiential | retrospective


@dataclass
class BatchResult:
    """Result of classifying a batch of propositions."""
    assignments: list[EvidenceRow]
    evidence_modes: dict[str, str]  # proposition_id → evidence_mode
    skipped: int                     # propositions assigned to 0 dimensions
    errors: int                      # parse failures within batch


# Batch size: 25 props × ~30 tokens each + 4 dimension descriptions + system prompt
# ≈ 1600 tokens input, ≈ 800 tokens output. Comfortable within Groq's limits.
BATCH_SIZE = 25


SYSTEM_PROMPT = """You are classifying propositions about a person into life dimensions.

You will receive a list of propositions extracted from conversations, and a set of dimension descriptions.

For each proposition, determine:
1. Which dimensions (0-3) this proposition informs. Most propositions map to exactly 1 dimension. Some span 2 (e.g., "career anxiety from childhood instability" → self + pursuits). A few map to 0 (meta-conversational, too generic).
2. Whether the evidence is experiential (present/recent — the person did, felt, or decided this) or retrospective (recounting history — "growing up...", "back in 2020...", "when I was...").

Think about what this proposition TELLS YOU about the person, not what topic it mentions.

Respond with valid JSON only. No markdown fences."""


def _build_batch_prompt(
    propositions: list[dict],
    dimensions: list[UserModelRow],
) -> str:
    """Build the user prompt for a batch of propositions."""
    dim_block = "\n".join(
        f"- **{d.id}**: {d.description}"
        for d in dimensions
    )

    prop_lines = []
    for i, p in enumerate(propositions):
        prop_lines.append(f'{i+1}. [{p["id"]}] ({p["node_type"]}) "{p["text"]}"')
    prop_block = "\n".join(prop_lines)

    return f"""## Dimensions

{dim_block}

## Propositions to classify

{prop_block}

## Response format

Return a JSON object with a "results" array. Each element must have:
- "id": the proposition ID (from brackets above)
- "dimensions": array of 0-3 dimension IDs from the list above
- "evidence_mode": "experiential" or "retrospective"

Example:
{{"results": [{{"id": "abc-123", "dimensions": ["self", "pursuits"], "evidence_mode": "experiential"}}]}}
"""


def _parse_batch_response(
    raw: str,
    valid_dim_ids: set[str],
    prop_ids_in_batch: set[str],
) -> tuple[list[AssignmentResult], int]:
    """Parse LLM response into AssignmentResults.

    Returns:
        (results, error_count) — results for successfully parsed props,
        count of props that failed parsing.
    """
    # Strip markdown fences if present
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
        # Entire batch failed to parse
        return [], len(prop_ids_in_batch)

    results_raw = data.get("results", [])
    if not isinstance(results_raw, list):
        return [], len(prop_ids_in_batch)

    results = []
    errors = 0

    for item in results_raw:
        try:
            prop_id = item["id"]
            if prop_id not in prop_ids_in_batch:
                errors += 1
                continue

            dims = item.get("dimensions", [])
            if not isinstance(dims, list):
                dims = []
            # Filter to valid dimension IDs only
            dims = [d for d in dims if d in valid_dim_ids]

            mode = item.get("evidence_mode", "experiential")
            if mode not in ("experiential", "retrospective"):
                mode = "experiential"

            results.append(AssignmentResult(
                proposition_id=prop_id,
                dimension_ids=dims,
                evidence_mode=mode,
            ))
        except (KeyError, TypeError):
            errors += 1

    # Count propositions that weren't in the response at all
    returned_ids = {r.proposition_id for r in results}
    missing = prop_ids_in_batch - returned_ids
    errors += len(missing)

    return results, errors


# ======================================================================
# Pass 2: Relevance + Direction scoring
# ======================================================================

@dataclass
class ScoreResult:
    """Result of scoring one (proposition, dimension) pair."""
    model_id: str
    proposition_id: str
    relevance: float      # 0.0-1.0
    direction: str        # supports | contradicts | contextualizes


@dataclass
class ScoreBatchResult:
    """Result of scoring a batch of assignments."""
    scores: list[ScoreResult]
    errors: int


SCORE_BATCH_SIZE = 20


SCORE_SYSTEM_PROMPT = """You are scoring how propositions about a person relate to specific life dimensions.

For each (proposition, dimension) pair, determine:
1. **relevance** (0.0-1.0): How strongly does this proposition inform understanding of this dimension?
   - 0.9-1.0: Central, defining evidence (e.g., "I identify as a builder" for self)
   - 0.6-0.8: Clearly relevant, meaningful evidence
   - 0.3-0.5: Tangentially relevant, provides some signal
   - 0.1-0.2: Weak connection, mostly noise for this dimension
2. **direction**: What is the proposition's relationship to this dimension?
   - "supports": Adds to or confirms understanding
   - "contradicts": Challenges or conflicts with other evidence in this dimension
   - "contextualizes": Provides background/framing without directly supporting or contradicting

Most propositions support their assigned dimension. Contradictions are rare but important —
they signal the person may be in transition or hold conflicting beliefs.

Respond with valid JSON only. No markdown fences."""


def _build_score_prompt(
    pairs: list[dict],
    dim_descriptions: dict[str, str],
) -> str:
    """Build prompt for scoring (proposition, dimension) pairs."""
    lines = []
    for i, p in enumerate(pairs):
        dim_desc = dim_descriptions.get(p["model_id"], p["model_id"])
        lines.append(
            f'{i+1}. [{p["proposition_id"]}→{p["model_id"]}] '
            f'Dimension "{p["model_id"]}": {dim_desc}\n'
            f'   Proposition ({p["node_type"]}): "{p["text"]}"'
        )
    pairs_block = "\n\n".join(lines)

    return f"""## Pairs to score

{pairs_block}

## Response format

Return a JSON object with a "scores" array. Each element must have:
- "proposition_id": the proposition ID
- "model_id": the dimension ID
- "relevance": float 0.0-1.0
- "direction": "supports" or "contradicts" or "contextualizes"

Example:
{{"scores": [{{"proposition_id": "abc-123", "model_id": "self", "relevance": 0.8, "direction": "supports"}}]}}
"""


def _parse_score_response(
    raw: str,
    expected_pairs: set[tuple[str, str]],
) -> tuple[list[ScoreResult], int]:
    """Parse scoring response. Returns (scores, error_count)."""
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
        return [], len(expected_pairs)

    scores_raw = data.get("scores", [])
    if not isinstance(scores_raw, list):
        return [], len(expected_pairs)

    results = []
    errors = 0

    for item in scores_raw:
        try:
            model_id = item["model_id"]
            prop_id = item["proposition_id"]
            pair = (model_id, prop_id)
            if pair not in expected_pairs:
                errors += 1
                continue

            relevance = float(item.get("relevance", 0.5))
            relevance = max(0.0, min(1.0, relevance))

            direction = item.get("direction", "supports")
            if direction not in ("supports", "contradicts", "contextualizes"):
                direction = "supports"

            results.append(ScoreResult(
                model_id=model_id,
                proposition_id=prop_id,
                relevance=round(relevance, 2),
                direction=direction,
            ))
        except (KeyError, TypeError, ValueError):
            errors += 1

    returned_pairs = {(r.model_id, r.proposition_id) for r in results}
    missing = expected_pairs - returned_pairs
    errors += len(missing)

    return results, errors


class AssignmentService:
    """Classifies propositions into user model dimensions via LLM."""

    def __init__(self, provider: Provider):
        self.provider = provider

    async def assign_batch(
        self,
        propositions: list[dict],
        dimensions: list[UserModelRow],
        batch_size: int = BATCH_SIZE,
    ) -> BatchResult:
        """Classify a list of propositions into dimensions.

        Args:
            propositions: Dicts with at least {id, text, node_type}
            dimensions: Active dimensions to classify into
            batch_size: Number of propositions per LLM call

        Returns:
            BatchResult with all assignments, evidence modes, skip/error counts.
        """
        valid_dim_ids = {d.id for d in dimensions}
        all_assignments: list[EvidenceRow] = []
        all_evidence_modes: dict[str, str] = {}
        total_skipped = 0
        total_errors = 0
        now = datetime.now(timezone.utc).isoformat()

        # Process in batches
        for i in range(0, len(propositions), batch_size):
            batch = propositions[i:i + batch_size]
            prop_ids = {p["id"] for p in batch}

            prompt = _build_batch_prompt(batch, dimensions)

            try:
                raw = await self.provider.complete(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    max_tokens=2048,
                )
            except ProviderError as e:
                print(f"  ⚠️ Batch {i//batch_size + 1} LLM call failed: {e}")
                total_errors += len(batch)
                continue

            results, errors = _parse_batch_response(raw, valid_dim_ids, prop_ids)
            total_errors += errors

            for r in results:
                all_evidence_modes[r.proposition_id] = r.evidence_mode

                if not r.dimension_ids:
                    total_skipped += 1
                    continue

                for dim_id in r.dimension_ids:
                    all_assignments.append(EvidenceRow(
                        model_id=dim_id,
                        proposition_id=r.proposition_id,
                        relevance=0.5,   # Default until Pass 2 scores
                        direction="supports",  # Default until Pass 2
                        assigned_at=now,
                        assigned_by="assignment_p1",
                    ))

            batch_num = i // batch_size + 1
            total_batches = (len(propositions) + batch_size - 1) // batch_size
            assigned_this = sum(1 for r in results if r.dimension_ids)
            print(f"  Batch {batch_num}/{total_batches}: {assigned_this} assigned, "
                  f"{sum(1 for r in results if not r.dimension_ids)} skipped, {errors} errors")

        return BatchResult(
            assignments=all_assignments,
            evidence_modes=all_evidence_modes,
            skipped=total_skipped,
            errors=total_errors,
        )

    async def score_batch(
        self,
        assignments: list[dict],
        dim_descriptions: dict[str, str],
        batch_size: int = SCORE_BATCH_SIZE,
    ) -> ScoreBatchResult:
        """Score relevance + direction for existing (proposition, dimension) pairs.

        Args:
            assignments: Dicts with {model_id, proposition_id, text, node_type}
            dim_descriptions: {dimension_id: description} for prompt context
            batch_size: Pairs per LLM call

        Returns:
            ScoreBatchResult with all scores and error count.
        """
        all_scores: list[ScoreResult] = []
        total_errors = 0

        for i in range(0, len(assignments), batch_size):
            batch = assignments[i:i + batch_size]
            expected = {(p["model_id"], p["proposition_id"]) for p in batch}

            prompt = _build_score_prompt(batch, dim_descriptions)

            try:
                raw = await self.provider.complete(
                    prompt=prompt,
                    system_prompt=SCORE_SYSTEM_PROMPT,
                    max_tokens=2048,
                )
            except ProviderError as e:
                print(f"  ⚠️ Score batch {i//batch_size + 1} failed: {e}")
                total_errors += len(batch)
                continue

            scores, errors = _parse_score_response(raw, expected)
            all_scores.extend(scores)
            total_errors += errors

            batch_num = i // batch_size + 1
            total_batches = (len(assignments) + batch_size - 1) // batch_size
            print(f"  Score batch {batch_num}/{total_batches}: {len(scores)} scored, {errors} errors")

        return ScoreBatchResult(scores=all_scores, errors=total_errors)
