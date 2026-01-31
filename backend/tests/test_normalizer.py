"""Tests for Normalizer service.

Normalizer responsibilities:
  - Map extracted variable names to canonical names via registry
  - Flag unknown variables for user review
  - Return stats on what matched vs what's new

NOT responsible for:
  - Saving data (that's storage.py)
  - Deciding what to do with unknowns (that's the UI/trainer)
"""
import pytest
from app.services.normalizer import normalize_extraction
from app.services.registry import VariableRegistry


@pytest.fixture
def registry(tmp_path):
    """Registry with some known variables."""
    r = VariableRegistry(path=tmp_path / "registry.json")
    r.add_variable("avg_heart_rate", "Avg Heart Rate", "bpm", aliases=["avg_hr", "heart_rate_avg"])
    r.add_variable("distance", "Distance", "km", aliases=["dist", "total_distance"])
    r.add_variable("workout_time", "Workout Time", "minutes", aliases=["duration", "time"])
    return r


@pytest.fixture
def empty_registry(tmp_path):
    """Registry with no variables."""
    return VariableRegistry(path=tmp_path / "registry.json")


class TestNormalizeKnownVariables:
    """Variables that exist in registry get normalized."""

    def test_exact_match_unchanged(self, registry):
        """Variable already using canonical name stays the same."""
        parsed = {
            "workout_type": "Indoor Cycle",
            "variables": {
                "distance": {"value": "21.56", "unit": "km"}
            }
        }
        result = normalize_extraction(parsed, registry)
        
        assert "distance" in result["normalized"]["variables"]
        assert result["normalized"]["variables"]["distance"]["value"] == "21.56"

    def test_alias_normalized_to_canonical(self, registry):
        """Variable using alias gets renamed to canonical."""
        parsed = {
            "workout_type": "Indoor Cycle",
            "variables": {
                "avg_hr": {"value": "143", "unit": "bpm"}
            }
        }
        result = normalize_extraction(parsed, registry)
        
        # "avg_hr" should become "avg_heart_rate"
        assert "avg_heart_rate" in result["normalized"]["variables"]
        assert "avg_hr" not in result["normalized"]["variables"]

    def test_case_insensitive_matching(self, registry):
        """Matching works regardless of case."""
        parsed = {
            "workout_type": "Run",
            "variables": {
                "AVG_HR": {"value": "150", "unit": "bpm"},
                "DISTANCE": {"value": "5.0", "unit": "km"}
            }
        }
        result = normalize_extraction(parsed, registry)
        
        assert "avg_heart_rate" in result["normalized"]["variables"]
        assert "distance" in result["normalized"]["variables"]


class TestNormalizeUnknownVariables:
    """Variables not in registry get flagged."""

    def test_unknown_variable_flagged(self, registry):
        """Variable not in registry appears in unknown list."""
        parsed = {
            "workout_type": "Indoor Cycle",
            "variables": {
                "distance": {"value": "21.56", "unit": "km"},
                "some_new_metric": {"value": "42", "unit": ""}
            }
        }
        result = normalize_extraction(parsed, registry)
        
        assert "some_new_metric" in result["unknown"]

    def test_unknown_variable_kept_in_output(self, registry):
        """Unknown variables still appear in normalized output (with original name)."""
        parsed = {
            "workout_type": "Indoor Cycle",
            "variables": {
                "brand_new_var": {"value": "100", "unit": "watts"}
            }
        }
        result = normalize_extraction(parsed, registry)
        
        # Still in output, just flagged as unknown
        assert "brand_new_var" in result["normalized"]["variables"]
        assert "brand_new_var" in result["unknown"]

    def test_all_unknown_with_empty_registry(self, empty_registry):
        """All variables flagged when registry is empty."""
        parsed = {
            "workout_type": "Run",
            "variables": {
                "pace": {"value": "5:30", "unit": "min/km"},
                "distance": {"value": "10", "unit": "km"}
            }
        }
        result = normalize_extraction(parsed, empty_registry)
        
        assert len(result["unknown"]) == 2
        assert "pace" in result["unknown"]
        assert "distance" in result["unknown"]


class TestNormalizeStats:
    """Stats track matching results."""

    def test_stats_all_matched(self, registry):
        """Stats show all matched when everything known."""
        parsed = {
            "workout_type": "Cycle",
            "variables": {
                "distance": {"value": "20", "unit": "km"},
                "avg_heart_rate": {"value": "140", "unit": "bpm"}
            }
        }
        result = normalize_extraction(parsed, registry)
        
        assert result["stats"]["matched"] == 2
        assert result["stats"]["total"] == 2

    def test_stats_partial_match(self, registry):
        """Stats show partial match."""
        parsed = {
            "workout_type": "Cycle",
            "variables": {
                "distance": {"value": "20", "unit": "km"},
                "unknown_var": {"value": "99", "unit": ""}
            }
        }
        result = normalize_extraction(parsed, registry)
        
        assert result["stats"]["matched"] == 1
        assert result["stats"]["total"] == 2

    def test_stats_none_matched(self, empty_registry):
        """Stats show zero matches with empty registry."""
        parsed = {
            "workout_type": "Run",
            "variables": {
                "x": {"value": "1", "unit": ""},
                "y": {"value": "2", "unit": ""}
            }
        }
        result = normalize_extraction(parsed, empty_registry)
        
        assert result["stats"]["matched"] == 0
        assert result["stats"]["total"] == 2


class TestNormalizeEdgeCases:
    """Edge cases and error handling."""

    def test_empty_variables(self, registry):
        """Handles empty variables dict."""
        parsed = {
            "workout_type": "Rest Day",
            "variables": {}
        }
        result = normalize_extraction(parsed, registry)
        
        assert result["normalized"]["variables"] == {}
        assert result["unknown"] == []
        assert result["stats"]["total"] == 0

    def test_preserves_workout_type(self, registry):
        """workout_type passes through unchanged."""
        parsed = {
            "workout_type": "Indoor Cycle",
            "variables": {
                "distance": {"value": "10", "unit": "km"}
            }
        }
        result = normalize_extraction(parsed, registry)
        
        assert result["normalized"]["workout_type"] == "Indoor Cycle"

    def test_preserves_variable_values(self, registry):
        """Value and unit preserved during normalization."""
        parsed = {
            "workout_type": "Run",
            "variables": {
                "avg_hr": {"value": "155", "unit": "bpm"}
            }
        }
        result = normalize_extraction(parsed, registry)
        
        normalized_var = result["normalized"]["variables"]["avg_heart_rate"]
        assert normalized_var["value"] == "155"
        assert normalized_var["unit"] == "bpm"
