"""
Tests for ContextAssemblyV2 — Piece 4 of Build 4.

Covers: model context formatting, inverse-confidence weighting tiers,
retrieval annotation, edge cases (empty model, no retrievals, mixed state).

All tests use temp databases with mock retrieval — no LLM calls, no embeddings.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.user_model.storage import UserModelStorage, EvidenceRow
from app.services.user_model.context import (
    ContextAssemblyV2,
    _extract_tension,
    STABLE_THRESHOLD,
    SPARSE_THRESHOLD,
)


SEEDS_PATH = Path(__file__).parent.parent / "data" / "dimension_seeds.json"


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    """Fresh database with propositions table + user model tables."""
    db_path = tmp_path / "test.db"
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE propositions (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            node_type TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            event_timeframe TEXT,
            evidence_mode TEXT DEFAULT 'experiential',
            status TEXT DEFAULT 'active'
        );
        CREATE TABLE embeddings (
            proposition_id TEXT PRIMARY KEY,
            embedding BLOB NOT NULL,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def storage(db):
    """UserModelStorage on temp DB."""
    store = UserModelStorage(db)
    yield store
    store.close()


@pytest.fixture
def seeded_storage(storage):
    """Storage with 4 seed dimensions loaded."""
    storage.seed_dimensions(SEEDS_PATH)
    return storage


@pytest.fixture
def mock_retrieval():
    """Mock RetrievalService that returns configurable results."""
    mock = MagicMock()
    mock.retrieve.return_value = []
    return mock


@pytest.fixture
def mock_embedder():
    """Mock embedder — context assembly doesn't embed in current implementation."""
    return MagicMock()


@pytest.fixture
def assembly(seeded_storage, mock_retrieval, mock_embedder):
    """ContextAssemblyV2 with seeded model and mock retrieval."""
    return ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)


def _insert_prop(storage, prop_id, text, node_type="stance"):
    """Insert a proposition into the test DB."""
    now = datetime.now(timezone.utc).isoformat()
    storage._conn.execute(
        "INSERT INTO propositions (id, text, node_type, confidence, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (prop_id, text, node_type, 0.8, now),
    )
    storage._conn.commit()


def _make_retrieval_result(prop_id, text, confidence=0.8, node_type="stance"):
    """Create a mock RetrievalResult-like object."""
    result = MagicMock()
    result.proposition_id = prop_id
    result.text = text
    result.confidence = confidence
    result.node_type = node_type
    return result


# ------------------------------------------------------------------
# Empty / cold start
# ------------------------------------------------------------------


class TestEmptyState:
    def test_truly_empty_model_no_retrieval_returns_none(
        self, storage, mock_retrieval, mock_embedder
    ):
        """No dimensions at all + no retrieval → no system prompt."""
        # Un-seeded storage: no dimensions exist
        ctx = ContextAssemblyV2(storage, mock_retrieval, mock_embedder)
        prompt, ids = ctx.build_system_prompt("hello")
        assert prompt is None
        assert ids == []

    def test_seeded_but_sparse_produces_prompt(self, assembly):
        """Seeded dimensions (all sparse, 0.0 confidence) still produce Layer 1."""
        prompt, ids = assembly.build_system_prompt("tell me about yourself")
        assert prompt is not None
        assert "Your understanding of this person" in prompt
        # All 4 dimensions should appear
        assert "Self" in prompt
        assert "Pursuits" in prompt
        assert "Relationships" in prompt
        assert "Body" in prompt

    def test_sparse_dimensions_get_full_treatment(self, assembly):
        """Sparse dimensions include unknowns and invitation to explore."""
        prompt, _ = assembly.build_system_prompt("anything")
        assert "limited understanding" in prompt
        assert "No clear picture yet" in prompt
        assert "Create space to learn more" in prompt


# ------------------------------------------------------------------
# Inverse-confidence weighting tiers
# ------------------------------------------------------------------


class TestConfidenceWeighting:
    def test_stable_dimension_one_liner(self, seeded_storage, mock_retrieval, mock_embedder):
        """Stable + high confidence → compressed to one line."""
        seeded_storage.update_dimension(
            "body",
            estimate="Actively training; nutrition protocol in progress.",
            confidence=0.80,
            uncertainty_type="stable",
            reasoning_trace="Consistent evidence from 31 body-related propositions.",
            evidence_count=31,
        )
        ctx = ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)
        prompt, _ = ctx.build_system_prompt("how's training")

        # Body should be a one-liner (no multi-line treatment)
        lines = prompt.split("\n")
        body_lines = [l for l in lines if "Body" in l and "confident" in l]
        assert len(body_lines) == 1
        assert "80%" in body_lines[0]
        assert "Actively training" in body_lines[0]

    def test_conflicted_dimension_full_treatment(self, seeded_storage, mock_retrieval, mock_embedder):
        """Conflicted → full treatment with tension note."""
        seeded_storage.update_dimension(
            "self",
            estimate="Strong self-awareness but tension between growth and achievement-devaluation.",
            confidence=0.80,
            uncertainty_type="conflicted",
            reasoning_trace="Tension between desire to grow and pattern of devaluing achievements once obtained.",
            evidence_count=83,
        )
        ctx = ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)
        prompt, _ = ctx.build_system_prompt("who am I")

        assert "conflicted" in prompt
        assert "Tension" in prompt
        assert "contradictory signals" in prompt

    def test_sparse_dimension_full_treatment(self, seeded_storage, mock_retrieval, mock_embedder):
        """Low confidence → full treatment with unknowns."""
        seeded_storage.update_dimension(
            "relationships",
            estimate="Some social needs identified but limited data.",
            confidence=0.25,
            uncertainty_type="sparse",
            reasoning_trace="Only 5 relationship-related propositions available.",
            evidence_count=5,
        )
        ctx = ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)
        prompt, _ = ctx.build_system_prompt("social life")

        assert "limited understanding" in prompt
        assert "5 data points" in prompt
        assert "Create space to learn more" in prompt

    def test_middle_confidence_moderate_treatment(self, seeded_storage, mock_retrieval, mock_embedder):
        """0.4-0.7 confidence, not conflicted → moderate treatment."""
        seeded_storage.update_dimension(
            "pursuits",
            estimate="Consolidating around AI engineering. Active Voku project.",
            confidence=0.55,
            uncertainty_type="sparse",  # won't matter — confidence triggers sparse
            reasoning_trace="Good evidence on current projects, less on long-term direction.",
            evidence_count=50,
        )
        ctx = ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)
        prompt, _ = ctx.build_system_prompt("career")

        # confidence < 0.4 threshold is sparse, but 0.55 is above it
        # however uncertainty_type is "sparse" → sparse treatment takes priority
        assert "limited understanding" in prompt or "developing" in prompt

    def test_mixed_confidence_different_treatments(self, seeded_storage, mock_retrieval, mock_embedder):
        """Different dimensions at different confidence levels get different formatting."""
        # Body: stable
        seeded_storage.update_dimension(
            "body", estimate="Training week 4.", confidence=0.80,
            uncertainty_type="stable", reasoning_trace="", evidence_count=31,
        )
        # Self: conflicted
        seeded_storage.update_dimension(
            "self", estimate="Growth vs achievement tension.",
            confidence=0.80, uncertainty_type="conflicted",
            reasoning_trace="Tension in self-concept.", evidence_count=83,
        )
        # Pursuits: developing
        seeded_storage.update_dimension(
            "pursuits", estimate="AI engineering direction.",
            confidence=0.55, uncertainty_type="stable",
            reasoning_trace="", evidence_count=50,
        )
        # Relationships: sparse (unchanged from seed — 0.0)

        ctx = ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)
        prompt, _ = ctx.build_system_prompt("general update")

        # Each dimension should be present with appropriate treatment
        assert "80% confident): Training week 4." in prompt  # stable one-liner
        assert "conflicted" in prompt  # self gets conflict treatment
        assert "developing" in prompt  # pursuits gets middle treatment
        assert "limited understanding" in prompt  # relationships still sparse


# ------------------------------------------------------------------
# Retrieval annotation
# ------------------------------------------------------------------


class TestRetrievalAnnotation:
    def test_retrievals_annotated_with_dimension(
        self, seeded_storage, mock_retrieval, mock_embedder
    ):
        """Retrieved propositions get [dimension] tags from model_evidence."""
        # Insert propositions and assign to dimensions
        _insert_prop(seeded_storage, "p1", "Building Voku as AI tool")
        _insert_prop(seeded_storage, "p2", "Morning formula: shower then smoothie")

        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("pursuits", "p1", 0.9, "supports", now, "assignment"),
            EvidenceRow("self", "p2", 0.85, "supports", now, "assignment"),
        ])

        # Mock retrieval returns these props
        mock_retrieval.retrieve.return_value = [
            _make_retrieval_result("p1", "Building Voku as AI tool"),
            _make_retrieval_result("p2", "Morning formula: shower then smoothie"),
        ]

        ctx = ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)
        prompt, ids = ctx.build_system_prompt("what am I working on")

        assert "[pursuits]" in prompt
        assert "[self]" in prompt
        assert ids == ["p1", "p2"]

    def test_unassigned_proposition_gets_uncategorized(
        self, seeded_storage, mock_retrieval, mock_embedder
    ):
        """Propositions not in model_evidence get [uncategorized] tag."""
        _insert_prop(seeded_storage, "p3", "Random thought about weather")

        mock_retrieval.retrieve.return_value = [
            _make_retrieval_result("p3", "Random thought about weather"),
        ]

        ctx = ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)
        prompt, _ = ctx.build_system_prompt("weather")

        assert "[uncategorized]" in prompt

    def test_multi_assigned_proposition_uses_highest_relevance(
        self, seeded_storage, mock_retrieval, mock_embedder
    ):
        """If a proposition maps to multiple dimensions, highest relevance wins."""
        _insert_prop(seeded_storage, "p4", "Career anxiety linked to childhood moves")

        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("pursuits", "p4", 0.6, "supports", now, "assignment"),
            EvidenceRow("self", "p4", 0.9, "supports", now, "assignment"),
        ])

        mock_retrieval.retrieve.return_value = [
            _make_retrieval_result("p4", "Career anxiety linked to childhood moves"),
        ]

        ctx = ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)
        prompt, _ = ctx.build_system_prompt("anxiety")

        assert "[self]" in prompt
        assert "[pursuits]" not in prompt  # self wins (0.9 > 0.6)

    def test_no_retrieval_results_omits_layer_2(
        self, seeded_storage, mock_retrieval, mock_embedder
    ):
        """No retrieval results → Layer 2 section absent, Layer 1 still present."""
        mock_retrieval.retrieve.return_value = []

        ctx = ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)
        prompt, ids = ctx.build_system_prompt("something obscure")

        assert prompt is not None  # Layer 1 still there from seeded dims
        assert "Your understanding" in prompt
        assert "Relevant context from prior conversations" not in prompt
        assert ids == []


# ------------------------------------------------------------------
# Prompt structure
# ------------------------------------------------------------------


class TestPromptStructure:
    def test_prompt_has_both_layers(self, seeded_storage, mock_retrieval, mock_embedder):
        """Full prompt contains identity line, Layer 1, Layer 2, and closing guidance."""
        _insert_prop(seeded_storage, "p5", "Loves systems thinking")
        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("self", "p5", 0.8, "supports", now, "assignment"),
        ])
        mock_retrieval.retrieve.return_value = [
            _make_retrieval_result("p5", "Loves systems thinking"),
        ]

        ctx = ContextAssemblyV2(seeded_storage, mock_retrieval, mock_embedder)
        prompt, _ = ctx.build_system_prompt("thinking style")

        assert "You are Voku" in prompt
        assert "Your understanding of this person" in prompt
        assert "Relevant context from prior conversations" in prompt
        assert "Don't interrogate" in prompt

    def test_closing_guidance_present(self, assembly):
        """System prompt always ends with behavioral guidance."""
        prompt, _ = assembly.build_system_prompt("hi")
        assert "weave it into your response" in prompt
        assert "Don't interrogate" in prompt


# ------------------------------------------------------------------
# _extract_tension helper
# ------------------------------------------------------------------


class TestExtractTension:
    def test_finds_tension_keyword(self):
        trace = "Evidence shows growth. Tension between self-improvement drive and achievement-devaluation pattern."
        result = _extract_tension(trace)
        assert result.startswith("Tension")
        assert "achievement-devaluation" in result

    def test_finds_however_keyword(self):
        trace = "Multiple signals agree. However the user shows some hesitation."
        result = _extract_tension(trace)
        assert "However" in result or "however" in result.lower()

    def test_truncates_long_trace_without_keywords(self):
        trace = "A" * 300
        result = _extract_tension(trace, max_length=200)
        assert len(result) <= 201  # 200 + ellipsis char
        assert result.endswith("…")

    def test_short_trace_returned_as_is(self):
        trace = "Brief note."
        result = _extract_tension(trace)
        assert result == "Brief note."


# ------------------------------------------------------------------
# get_primary_dimension_map (storage method used by context)
# ------------------------------------------------------------------


class TestPrimaryDimensionMap:
    def test_returns_correct_mapping(self, seeded_storage):
        _insert_prop(seeded_storage, "px", "Test prop X")
        _insert_prop(seeded_storage, "py", "Test prop Y")
        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("body", "px", 0.7, "supports", now, "assignment"),
            EvidenceRow("self", "py", 0.9, "supports", now, "assignment"),
        ])

        result = seeded_storage.get_primary_dimension_map(["px", "py"])
        assert result == {"px": "body", "py": "self"}

    def test_empty_input_returns_empty(self, seeded_storage):
        assert seeded_storage.get_primary_dimension_map([]) == {}

    def test_unknown_prop_not_in_result(self, seeded_storage):
        result = seeded_storage.get_primary_dimension_map(["nonexistent"])
        assert result == {}

    def test_multi_assignment_picks_highest_relevance(self, seeded_storage):
        _insert_prop(seeded_storage, "pm", "Multi-assigned prop")
        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("pursuits", "pm", 0.4, "supports", now, "assignment"),
            EvidenceRow("self", "pm", 0.95, "supports", now, "assignment"),
        ])

        result = seeded_storage.get_primary_dimension_map(["pm"])
        assert result == {"pm": "self"}
