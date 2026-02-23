"""
Tests for AssignmentService — Piece 2 of Build 4.

Covers:
  - Prompt construction
  - Response parsing (valid, partial, malformed, edge cases)
  - Batch processing with mock provider
  - Evidence mode classification
  - Dimension filtering (invalid IDs rejected)
"""

import json
from datetime import datetime, timezone

import pytest

from app.services.user_model.assignment import (
    AssignmentService,
    AssignmentResult,
    BatchResult,
    _build_batch_prompt,
    _parse_batch_response,
    BATCH_SIZE,
)
from app.services.user_model.storage import UserModelRow, EvidenceRow


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

SEED_DIMS = [
    UserModelRow(
        id="self", dimension="self", subdimension=None,
        description="Identity, values, self-concept, emotional life",
        estimate="", confidence=0.0, uncertainty_type="sparse",
        evidence_count=0, last_updated="", last_evidence_at=None,
        decay_class="core", decay_rate=None,
    ),
    UserModelRow(
        id="pursuits", dimension="pursuits", subdimension=None,
        description="Career, projects, goals, plans, skills",
        estimate="", confidence=0.0, uncertainty_type="sparse",
        evidence_count=0, last_updated="", last_evidence_at=None,
        decay_class="preference", decay_rate=None,
    ),
    UserModelRow(
        id="relationships", dimension="relationships", subdimension=None,
        description="Connections, family, friends, social needs",
        estimate="", confidence=0.0, uncertainty_type="sparse",
        evidence_count=0, last_updated="", last_evidence_at=None,
        decay_class="preference", decay_rate=None,
    ),
    UserModelRow(
        id="body", dimension="body", subdimension=None,
        description="Health, fitness, energy, nutrition, sleep",
        estimate="", confidence=0.0, uncertainty_type="sparse",
        evidence_count=0, last_updated="", last_evidence_at=None,
        decay_class="situational", decay_rate=None,
    ),
]

VALID_DIM_IDS = {"self", "pursuits", "relationships", "body"}

SAMPLE_PROPS = [
    {"id": "p1", "text": "Morning formula is load-bearing for my day", "node_type": "stance"},
    {"id": "p2", "text": "Building Voku as AI-powered context engine", "node_type": "intention"},
    {"id": "p3", "text": "Miss having close friends in Vancouver", "node_type": "stance"},
    {"id": "p4", "text": "2K row time is 8:05, targeting sub-8:00", "node_type": "event"},
    {"id": "p5", "text": "Career anxiety connects to childhood instability", "node_type": "stance"},
]


# ------------------------------------------------------------------
# Prompt construction
# ------------------------------------------------------------------

class TestPromptConstruction:
    def test_prompt_includes_all_dimensions(self):
        prompt = _build_batch_prompt(SAMPLE_PROPS[:2], SEED_DIMS)
        assert "**self**" in prompt
        assert "**pursuits**" in prompt
        assert "**relationships**" in prompt
        assert "**body**" in prompt

    def test_prompt_includes_all_propositions(self):
        prompt = _build_batch_prompt(SAMPLE_PROPS[:3], SEED_DIMS)
        assert "p1" in prompt
        assert "p2" in prompt
        assert "p3" in prompt
        assert "Morning formula" in prompt

    def test_prompt_includes_node_types(self):
        prompt = _build_batch_prompt(SAMPLE_PROPS[:1], SEED_DIMS)
        assert "(stance)" in prompt

    def test_prompt_includes_response_format(self):
        prompt = _build_batch_prompt(SAMPLE_PROPS[:1], SEED_DIMS)
        assert '"results"' in prompt
        assert '"dimensions"' in prompt
        assert '"evidence_mode"' in prompt


# ------------------------------------------------------------------
# Response parsing
# ------------------------------------------------------------------

class TestParsing:
    def test_valid_single_dimension(self):
        raw = json.dumps({"results": [
            {"id": "p1", "dimensions": ["self"], "evidence_mode": "experiential"},
        ]})
        results, errors = _parse_batch_response(raw, VALID_DIM_IDS, {"p1"})
        assert len(results) == 1
        assert results[0].dimension_ids == ["self"]
        assert results[0].evidence_mode == "experiential"
        assert errors == 0

    def test_valid_multi_dimension(self):
        raw = json.dumps({"results": [
            {"id": "p5", "dimensions": ["self", "pursuits"], "evidence_mode": "retrospective"},
        ]})
        results, errors = _parse_batch_response(raw, VALID_DIM_IDS, {"p5"})
        assert results[0].dimension_ids == ["self", "pursuits"]

    def test_valid_zero_dimensions(self):
        raw = json.dumps({"results": [
            {"id": "p1", "dimensions": [], "evidence_mode": "experiential"},
        ]})
        results, errors = _parse_batch_response(raw, VALID_DIM_IDS, {"p1"})
        assert results[0].dimension_ids == []

    def test_invalid_dimension_filtered(self):
        raw = json.dumps({"results": [
            {"id": "p1", "dimensions": ["self", "finance", "bogus"], "evidence_mode": "experiential"},
        ]})
        results, errors = _parse_batch_response(raw, VALID_DIM_IDS, {"p1"})
        assert results[0].dimension_ids == ["self"]

    def test_invalid_evidence_mode_defaults(self):
        raw = json.dumps({"results": [
            {"id": "p1", "dimensions": ["self"], "evidence_mode": "something_wrong"},
        ]})
        results, _ = _parse_batch_response(raw, VALID_DIM_IDS, {"p1"})
        assert results[0].evidence_mode == "experiential"

    def test_missing_evidence_mode_defaults(self):
        raw = json.dumps({"results": [
            {"id": "p1", "dimensions": ["self"]},
        ]})
        results, _ = _parse_batch_response(raw, VALID_DIM_IDS, {"p1"})
        assert results[0].evidence_mode == "experiential"

    def test_markdown_fences_stripped(self):
        raw = '```json\n{"results": [{"id": "p1", "dimensions": ["self"], "evidence_mode": "experiential"}]}\n```'
        results, errors = _parse_batch_response(raw, VALID_DIM_IDS, {"p1"})
        assert len(results) == 1
        assert errors == 0

    def test_invalid_json_returns_all_errors(self):
        results, errors = _parse_batch_response("not json at all", VALID_DIM_IDS, {"p1", "p2"})
        assert results == []
        assert errors == 2

    def test_missing_results_key(self):
        raw = json.dumps({"classifications": []})
        results, errors = _parse_batch_response(raw, VALID_DIM_IDS, {"p1"})
        assert results == []
        assert errors == 1

    def test_unknown_prop_id_counted_as_error(self):
        raw = json.dumps({"results": [
            {"id": "unknown_id", "dimensions": ["self"], "evidence_mode": "experiential"},
        ]})
        results, errors = _parse_batch_response(raw, VALID_DIM_IDS, {"p1"})
        assert len(results) == 0
        assert errors == 2  # 1 for unknown ID + 1 for missing p1

    def test_missing_prop_in_response_counted(self):
        raw = json.dumps({"results": [
            {"id": "p1", "dimensions": ["self"], "evidence_mode": "experiential"},
        ]})
        # Batch had p1 and p2, but response only returned p1
        results, errors = _parse_batch_response(raw, VALID_DIM_IDS, {"p1", "p2"})
        assert len(results) == 1
        assert errors == 1  # p2 missing

    def test_batch_of_five(self):
        raw = json.dumps({"results": [
            {"id": "p1", "dimensions": ["self"], "evidence_mode": "experiential"},
            {"id": "p2", "dimensions": ["pursuits"], "evidence_mode": "experiential"},
            {"id": "p3", "dimensions": ["relationships"], "evidence_mode": "experiential"},
            {"id": "p4", "dimensions": ["body"], "evidence_mode": "experiential"},
            {"id": "p5", "dimensions": ["self", "pursuits"], "evidence_mode": "retrospective"},
        ]})
        prop_ids = {"p1", "p2", "p3", "p4", "p5"}
        results, errors = _parse_batch_response(raw, VALID_DIM_IDS, prop_ids)
        assert len(results) == 5
        assert errors == 0
        modes = {r.proposition_id: r.evidence_mode for r in results}
        assert modes["p5"] == "retrospective"


# ------------------------------------------------------------------
# Mock provider for integration tests
# ------------------------------------------------------------------

class MockProvider:
    """Returns pre-configured responses for testing."""

    def __init__(self, responses: list[str]):
        self.responses = responses
        self.call_count = 0
        self.prompts: list[str] = []

    async def complete(self, prompt: str, **kwargs) -> str:
        self.prompts.append(prompt)
        idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1
        return self.responses[idx]


class MockFailProvider:
    """Always raises ProviderError."""

    async def complete(self, prompt: str, **kwargs) -> str:
        from app.services.providers.base import ProviderError
        raise ProviderError("Mock failure")


# ------------------------------------------------------------------
# Integration: assign_batch with mock provider
# ------------------------------------------------------------------

class TestAssignBatch:
    @pytest.mark.asyncio
    async def test_basic_assignment(self):
        response = json.dumps({"results": [
            {"id": "p1", "dimensions": ["self"], "evidence_mode": "experiential"},
            {"id": "p2", "dimensions": ["pursuits"], "evidence_mode": "experiential"},
        ]})
        provider = MockProvider([response])
        service = AssignmentService(provider)

        result = await service.assign_batch(
            SAMPLE_PROPS[:2], SEED_DIMS, batch_size=25,
        )

        assert len(result.assignments) == 2
        assert result.skipped == 0
        assert result.errors == 0
        dim_ids = {a.model_id for a in result.assignments}
        assert "self" in dim_ids
        assert "pursuits" in dim_ids

    @pytest.mark.asyncio
    async def test_multi_dimension_creates_multiple_evidence_rows(self):
        response = json.dumps({"results": [
            {"id": "p5", "dimensions": ["self", "pursuits"], "evidence_mode": "retrospective"},
        ]})
        provider = MockProvider([response])
        service = AssignmentService(provider)

        result = await service.assign_batch(
            [SAMPLE_PROPS[4]], SEED_DIMS, batch_size=25,
        )

        # 1 proposition → 2 dimension assignments
        assert len(result.assignments) == 2
        models = {a.model_id for a in result.assignments}
        assert models == {"self", "pursuits"}
        assert result.evidence_modes["p5"] == "retrospective"

    @pytest.mark.asyncio
    async def test_zero_dimensions_counted_as_skipped(self):
        response = json.dumps({"results": [
            {"id": "p1", "dimensions": [], "evidence_mode": "experiential"},
        ]})
        provider = MockProvider([response])
        service = AssignmentService(provider)

        result = await service.assign_batch(
            SAMPLE_PROPS[:1], SEED_DIMS, batch_size=25,
        )

        assert len(result.assignments) == 0
        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_batching_splits_large_input(self):
        # 5 props with batch_size=2 → 3 LLM calls
        responses = [
            json.dumps({"results": [
                {"id": "p1", "dimensions": ["self"], "evidence_mode": "experiential"},
                {"id": "p2", "dimensions": ["pursuits"], "evidence_mode": "experiential"},
            ]}),
            json.dumps({"results": [
                {"id": "p3", "dimensions": ["relationships"], "evidence_mode": "experiential"},
                {"id": "p4", "dimensions": ["body"], "evidence_mode": "experiential"},
            ]}),
            json.dumps({"results": [
                {"id": "p5", "dimensions": ["self", "pursuits"], "evidence_mode": "retrospective"},
            ]}),
        ]
        provider = MockProvider(responses)
        service = AssignmentService(provider)

        result = await service.assign_batch(
            SAMPLE_PROPS, SEED_DIMS, batch_size=2,
        )

        assert provider.call_count == 3
        # p1→self, p2→pursuits, p3→rel, p4→body, p5→self+pursuits = 6 assignments
        assert len(result.assignments) == 6

    @pytest.mark.asyncio
    async def test_provider_failure_records_errors(self):
        provider = MockFailProvider()
        service = AssignmentService(provider)

        result = await service.assign_batch(
            SAMPLE_PROPS[:2], SEED_DIMS, batch_size=25,
        )

        assert len(result.assignments) == 0
        assert result.errors == 2

    @pytest.mark.asyncio
    async def test_default_relevance_and_direction(self):
        response = json.dumps({"results": [
            {"id": "p1", "dimensions": ["self"], "evidence_mode": "experiential"},
        ]})
        provider = MockProvider([response])
        service = AssignmentService(provider)

        result = await service.assign_batch(
            SAMPLE_PROPS[:1], SEED_DIMS, batch_size=25,
        )

        assert result.assignments[0].relevance == 0.5
        assert result.assignments[0].direction == "supports"
        assert result.assignments[0].assigned_by == "assignment_p1"


# ------------------------------------------------------------------
# Pass 2: Scoring prompt + parsing
# ------------------------------------------------------------------

from app.services.user_model.assignment import (
    ScoreResult,
    ScoreBatchResult,
    _build_score_prompt,
    _parse_score_response,
)

DIM_DESCRIPTIONS = {
    "self": "Identity, values, self-concept, emotional life",
    "pursuits": "Career, projects, goals, plans, skills",
    "relationships": "Connections, family, friends, social needs",
    "body": "Health, fitness, energy, nutrition, sleep",
}


class TestScorePrompt:
    def test_includes_dimension_description(self):
        pairs = [{"proposition_id": "p1", "model_id": "self", "text": "I value focus", "node_type": "stance"}]
        prompt = _build_score_prompt(pairs, DIM_DESCRIPTIONS)
        assert "Identity, values, self-concept" in prompt

    def test_includes_proposition_text(self):
        pairs = [{"proposition_id": "p1", "model_id": "self", "text": "I value focus", "node_type": "stance"}]
        prompt = _build_score_prompt(pairs, DIM_DESCRIPTIONS)
        assert "I value focus" in prompt

    def test_includes_response_format(self):
        pairs = [{"proposition_id": "p1", "model_id": "self", "text": "test", "node_type": "stance"}]
        prompt = _build_score_prompt(pairs, DIM_DESCRIPTIONS)
        assert '"relevance"' in prompt
        assert '"direction"' in prompt


class TestScoreParsing:
    def test_valid_score(self):
        raw = json.dumps({"scores": [
            {"proposition_id": "p1", "model_id": "self", "relevance": 0.85, "direction": "supports"},
        ]})
        scores, errors = _parse_score_response(raw, {("self", "p1")})
        assert len(scores) == 1
        assert scores[0].relevance == 0.85
        assert scores[0].direction == "supports"
        assert errors == 0

    def test_contradicts_direction(self):
        raw = json.dumps({"scores": [
            {"proposition_id": "p1", "model_id": "self", "relevance": 0.7, "direction": "contradicts"},
        ]})
        scores, _ = _parse_score_response(raw, {("self", "p1")})
        assert scores[0].direction == "contradicts"

    def test_contextualizes_direction(self):
        raw = json.dumps({"scores": [
            {"proposition_id": "p1", "model_id": "self", "relevance": 0.4, "direction": "contextualizes"},
        ]})
        scores, _ = _parse_score_response(raw, {("self", "p1")})
        assert scores[0].direction == "contextualizes"

    def test_relevance_clamped_high(self):
        raw = json.dumps({"scores": [
            {"proposition_id": "p1", "model_id": "self", "relevance": 1.5, "direction": "supports"},
        ]})
        scores, _ = _parse_score_response(raw, {("self", "p1")})
        assert scores[0].relevance == 1.0

    def test_relevance_clamped_low(self):
        raw = json.dumps({"scores": [
            {"proposition_id": "p1", "model_id": "self", "relevance": -0.3, "direction": "supports"},
        ]})
        scores, _ = _parse_score_response(raw, {("self", "p1")})
        assert scores[0].relevance == 0.0

    def test_invalid_direction_defaults(self):
        raw = json.dumps({"scores": [
            {"proposition_id": "p1", "model_id": "self", "relevance": 0.5, "direction": "neutral"},
        ]})
        scores, _ = _parse_score_response(raw, {("self", "p1")})
        assert scores[0].direction == "supports"

    def test_missing_pair_counted_as_error(self):
        raw = json.dumps({"scores": [
            {"proposition_id": "p1", "model_id": "self", "relevance": 0.8, "direction": "supports"},
        ]})
        scores, errors = _parse_score_response(raw, {("self", "p1"), ("pursuits", "p2")})
        assert len(scores) == 1
        assert errors == 1

    def test_unknown_pair_counted_as_error(self):
        raw = json.dumps({"scores": [
            {"proposition_id": "p99", "model_id": "body", "relevance": 0.5, "direction": "supports"},
        ]})
        scores, errors = _parse_score_response(raw, {("self", "p1")})
        assert len(scores) == 0
        assert errors == 2  # unknown pair + missing p1

    def test_invalid_json(self):
        scores, errors = _parse_score_response("broken", {("self", "p1")})
        assert scores == []
        assert errors == 1

    def test_markdown_fences_stripped(self):
        raw = '```json\n{"scores": [{"proposition_id": "p1", "model_id": "self", "relevance": 0.7, "direction": "supports"}]}\n```'
        scores, errors = _parse_score_response(raw, {("self", "p1")})
        assert len(scores) == 1
        assert errors == 0

    def test_multiple_scores(self):
        raw = json.dumps({"scores": [
            {"proposition_id": "p1", "model_id": "self", "relevance": 0.9, "direction": "supports"},
            {"proposition_id": "p2", "model_id": "pursuits", "relevance": 0.6, "direction": "contextualizes"},
            {"proposition_id": "p3", "model_id": "body", "relevance": 0.3, "direction": "supports"},
        ]})
        expected = {("self", "p1"), ("pursuits", "p2"), ("body", "p3")}
        scores, errors = _parse_score_response(raw, expected)
        assert len(scores) == 3
        assert errors == 0


class TestScoreBatch:
    @pytest.mark.asyncio
    async def test_basic_scoring(self):
        response = json.dumps({"scores": [
            {"proposition_id": "p1", "model_id": "self", "relevance": 0.85, "direction": "supports"},
            {"proposition_id": "p2", "model_id": "pursuits", "relevance": 0.7, "direction": "supports"},
        ]})
        provider = MockProvider([response])
        service = AssignmentService(provider)

        assignments = [
            {"model_id": "self", "proposition_id": "p1", "text": "I value focus", "node_type": "stance"},
            {"model_id": "pursuits", "proposition_id": "p2", "text": "Building Voku", "node_type": "intention"},
        ]
        result = await service.score_batch(assignments, DIM_DESCRIPTIONS)

        assert len(result.scores) == 2
        assert result.errors == 0
        by_prop = {s.proposition_id: s for s in result.scores}
        assert by_prop["p1"].relevance == 0.85
        assert by_prop["p2"].relevance == 0.7

    @pytest.mark.asyncio
    async def test_scoring_batches_correctly(self):
        r1 = json.dumps({"scores": [
            {"proposition_id": "p1", "model_id": "self", "relevance": 0.9, "direction": "supports"},
        ]})
        r2 = json.dumps({"scores": [
            {"proposition_id": "p2", "model_id": "pursuits", "relevance": 0.6, "direction": "supports"},
        ]})
        provider = MockProvider([r1, r2])
        service = AssignmentService(provider)

        assignments = [
            {"model_id": "self", "proposition_id": "p1", "text": "test", "node_type": "stance"},
            {"model_id": "pursuits", "proposition_id": "p2", "text": "test", "node_type": "stance"},
        ]
        result = await service.score_batch(assignments, DIM_DESCRIPTIONS, batch_size=1)

        assert provider.call_count == 2
        assert len(result.scores) == 2

    @pytest.mark.asyncio
    async def test_provider_failure_records_errors(self):
        provider = MockFailProvider()
        service = AssignmentService(provider)

        assignments = [
            {"model_id": "self", "proposition_id": "p1", "text": "test", "node_type": "stance"},
        ]
        result = await service.score_batch(assignments, DIM_DESCRIPTIONS)
        assert result.errors == 1
        assert len(result.scores) == 0
