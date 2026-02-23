"""
Tests for ExhaleService — Piece 3 of Build 4.

Tests the deterministic parts: response parsing, threshold gate,
citation checking. LLM integration tested via migration script.
"""

import numpy as np
import pytest

from app.services.user_model.inference import (
    _parse_exhale_response,
    _check_citation,
    ExhaleService,
    SEMANTIC_SIMILARITY_THRESHOLD,
    CONFIDENCE_DELTA_THRESHOLD,
)


# ======================================================================
# Response parsing
# ======================================================================

class TestParseExhaleResponse:
    """Test _parse_exhale_response with various LLM outputs."""

    def test_valid_response(self):
        raw = '''{
            "estimate": "This person is deeply driven by building tools.",
            "confidence": 0.72,
            "uncertainty_type": "stable",
            "reasoning_trace": "Based on [abc-123] and [def-456], consistent pattern.",
            "goal_ids": ["goal-1", "goal-2"]
        }'''
        result = _parse_exhale_response(raw)
        assert result is not None
        assert result["estimate"] == "This person is deeply driven by building tools."
        assert result["confidence"] == 0.72
        assert result["uncertainty_type"] == "stable"
        assert "abc-123" in result["reasoning_trace"]
        assert result["goal_ids"] == ["goal-1", "goal-2"]

    def test_with_markdown_fences(self):
        raw = '```json\n{"estimate": "Test.", "confidence": 0.5, "uncertainty_type": "sparse", "reasoning_trace": "x", "goal_ids": []}\n```'
        result = _parse_exhale_response(raw)
        assert result is not None
        assert result["estimate"] == "Test."

    def test_invalid_json(self):
        result = _parse_exhale_response("not json at all")
        assert result is None

    def test_missing_estimate(self):
        raw = '{"confidence": 0.5, "uncertainty_type": "sparse"}'
        result = _parse_exhale_response(raw)
        assert result is None

    def test_empty_estimate(self):
        raw = '{"estimate": "", "confidence": 0.5}'
        result = _parse_exhale_response(raw)
        assert result is None

    def test_confidence_clamped(self):
        raw = '{"estimate": "Test.", "confidence": 1.5, "uncertainty_type": "stable", "reasoning_trace": "x"}'
        result = _parse_exhale_response(raw)
        assert result["confidence"] == 1.0

    def test_confidence_clamped_negative(self):
        raw = '{"estimate": "Test.", "confidence": -0.3, "uncertainty_type": "stable", "reasoning_trace": "x"}'
        result = _parse_exhale_response(raw)
        assert result["confidence"] == 0.0

    def test_invalid_uncertainty_type_defaults(self):
        raw = '{"estimate": "Test.", "confidence": 0.5, "uncertainty_type": "unknown_value", "reasoning_trace": "x"}'
        result = _parse_exhale_response(raw)
        assert result["uncertainty_type"] == "sparse"

    def test_missing_optional_fields(self):
        raw = '{"estimate": "Test.", "confidence": 0.5}'
        result = _parse_exhale_response(raw)
        assert result is not None
        assert result["uncertainty_type"] == "sparse"
        assert result["reasoning_trace"] == ""
        assert result["goal_ids"] == []

    def test_goal_ids_filters_non_strings(self):
        raw = '{"estimate": "Test.", "confidence": 0.5, "goal_ids": ["valid", 123, null, "also-valid"]}'
        result = _parse_exhale_response(raw)
        assert result["goal_ids"] == ["valid", "also-valid"]


# ======================================================================
# Citation checking
# ======================================================================

class TestCheckCitation:
    """Test _check_citation with various reasoning traces."""

    def test_full_id_match(self):
        evidence = [{"proposition_id": "abc-123-def-456"}]
        assert _check_citation("Based on [abc-123-def-456]", evidence) is True

    def test_short_id_match(self):
        evidence = [{"proposition_id": "abc12345-6789-etc"}]
        assert _check_citation("Evidence from abc12345 shows...", evidence) is True

    def test_no_match(self):
        evidence = [{"proposition_id": "abc-123"}]
        assert _check_citation("General reasoning without citations.", evidence) is False

    def test_empty_trace(self):
        evidence = [{"proposition_id": "abc-123"}]
        assert _check_citation("", evidence) is False

    def test_empty_evidence(self):
        assert _check_citation("Some trace", []) is False

    def test_multiple_evidence_one_cited(self):
        evidence = [
            {"proposition_id": "first-id"},
            {"proposition_id": "second-id"},
            {"proposition_id": "third-id"},
        ]
        assert _check_citation("Only second-id was relevant.", evidence) is True


# ======================================================================
# Threshold gate
# ======================================================================

class TestThresholdGate:
    """Test the threshold gate with mock embedder."""

    class MockEmbedder:
        """Returns predictable embeddings for gate testing."""
        def __init__(self, similarity: float):
            self._similarity = similarity

        def embed(self, text: str) -> np.ndarray:
            # Create vectors with desired cosine similarity
            if "old" in text.lower() or text == self._old_text:
                return np.array([1.0, 0.0, 0.0])
            else:
                # Construct vector with target similarity to [1,0,0]
                s = self._similarity
                return np.array([s, np.sqrt(1 - s**2), 0.0])

    @staticmethod
    def _make_service(similarity: float):
        """Create ExhaleService with mock embedder at given similarity."""

        class FixedEmbedder:
            """Returns [1,0,0] for old estimate, vector with target sim for new."""
            def __init__(self, sim):
                self.sim = sim
                self._call_count = 0

            def embed(self, text: str) -> np.ndarray:
                self._call_count += 1
                if self._call_count == 1:  # old estimate
                    return np.array([1.0, 0.0, 0.0], dtype=np.float32)
                else:  # new estimate
                    s = self.sim
                    return np.array([s, np.sqrt(1 - s**2), 0.0], dtype=np.float32)

        embedder = FixedEmbedder(similarity)
        # We only need the _threshold_gate method, not full service
        service = ExhaleService.__new__(ExhaleService)
        service.embedder = embedder
        return service

    def test_first_exhale_always_passes(self):
        """No old estimate → gate always passes (first run)."""
        service = self._make_service(0.99)
        evidence = [{"proposition_id": "abc-123"}]
        passed, reason = service._threshold_gate(
            old_estimate="",  # empty = first exhale
            new_estimate="New estimate.",
            old_confidence=0.0,
            new_confidence=0.5,
            reasoning_trace="Based on abc-123",
            evidence=evidence,
        )
        assert passed is True
        assert reason is None

    def test_high_similarity_fails(self):
        """Near-identical rephrasing should not pass."""
        service = self._make_service(0.95)
        evidence = [{"proposition_id": "abc-123"}]
        passed, reason = service._threshold_gate(
            old_estimate="Old estimate about pursuits.",
            new_estimate="Similar estimate about pursuits.",
            old_confidence=0.5,
            new_confidence=0.6,
            reasoning_trace="Based on abc-123",
            evidence=evidence,
        )
        assert passed is False
        assert "semantic_delta" in reason

    def test_large_semantic_shift_passes(self):
        """Genuinely different estimate should pass."""
        service = self._make_service(0.6)
        evidence = [{"proposition_id": "abc-123"}]
        passed, reason = service._threshold_gate(
            old_estimate="Old estimate.",
            new_estimate="Completely different assessment.",
            old_confidence=0.3,
            new_confidence=0.7,
            reasoning_trace="abc-123 changed my view",
            evidence=evidence,
        )
        assert passed is True

    def test_no_citation_fails(self):
        """Gate requires evidence citation in reasoning trace."""
        service = self._make_service(0.6)
        evidence = [{"proposition_id": "abc-123"}]
        passed, reason = service._threshold_gate(
            old_estimate="Old.",
            new_estimate="New and different.",
            old_confidence=0.3,
            new_confidence=0.7,
            reasoning_trace="General reasoning without any specific references.",
            evidence=evidence,
        )
        assert passed is False
        assert "citation" in reason

    def test_moderate_similarity_small_confidence_delta_fails(self):
        """Borderline semantic + small confidence → fail."""
        service = self._make_service(0.88)
        evidence = [{"proposition_id": "abc-123"}]
        passed, reason = service._threshold_gate(
            old_estimate="Old.",
            new_estimate="Slightly different.",
            old_confidence=0.5,
            new_confidence=0.55,  # delta = 0.05 < 0.1
            reasoning_trace="abc-123 noted",
            evidence=evidence,
        )
        assert passed is False
        assert "confidence_delta" in reason
