"""Tests for Variable Registry.

Registry responsibilities:
  - Store canonical variable names
  - Map aliases to canonical names
  - Track observation counts

NOT responsible for (see Trainer agent, v0.2):
  - Deciding which variables matter
  - Comparing against training plans
  - Prioritizing variables
"""
import os
import json
import pytest
from app.services.registry import VariableRegistry


class TestRegistryLoad:
    """Loading registry from disk."""

    def test_load_empty_registry(self, tmp_path):
        """Returns empty dict if file doesn't exist."""
        registry = VariableRegistry(path=tmp_path / "registry.json")
        assert registry.variables == {}

    def test_load_existing_registry(self, tmp_path):
        """Loads existing registry from file."""
        registry_file = tmp_path / "registry.json"
        registry_file.write_text(json.dumps({
            "avg_heart_rate": {
                "display": "Avg Heart Rate",
                "aliases": ["avg_hr"],
                "unit": "bpm",
                "count": 1
            }
        }))
        registry = VariableRegistry(path=registry_file)
        assert "avg_heart_rate" in registry.variables


class TestRegistryLookup:
    """Finding canonical names."""

    def test_get_canonical_exact_match(self, tmp_path):
        """Direct match on canonical name."""
        registry = VariableRegistry(path=tmp_path / "registry.json")
        registry.variables = {
            "avg_heart_rate": {"display": "Avg Heart Rate", "aliases": [], "unit": "bpm", "count": 1}
        }
        assert registry.get_canonical("avg_heart_rate") == "avg_heart_rate"

    def test_get_canonical_via_alias(self, tmp_path):
        """Match through alias."""
        registry = VariableRegistry(path=tmp_path / "registry.json")
        registry.variables = {
            "avg_heart_rate": {"display": "Avg Heart Rate", "aliases": ["avg_hr", "heart_rate_avg"], "unit": "bpm", "count": 1}
        }
        assert registry.get_canonical("avg_hr") == "avg_heart_rate"
        assert registry.get_canonical("heart_rate_avg") == "avg_heart_rate"

    def test_get_canonical_case_insensitive(self, tmp_path):
        """Lookup ignores case."""
        registry = VariableRegistry(path=tmp_path / "registry.json")
        registry.variables = {
            "avg_heart_rate": {"display": "Avg Heart Rate", "aliases": ["Avg HR"], "unit": "bpm", "count": 1}
        }
        assert registry.get_canonical("AVG_HEART_RATE") == "avg_heart_rate"
        assert registry.get_canonical("avg hr") == "avg_heart_rate"

    def test_get_canonical_unknown_returns_none(self, tmp_path):
        """Unknown variable returns None."""
        registry = VariableRegistry(path=tmp_path / "registry.json")
        registry.variables = {}
        assert registry.get_canonical("some_new_metric") is None


class TestRegistryWrite:
    """Adding and updating variables."""

    def test_add_variable(self, tmp_path):
        """Adds new variable to registry."""
        registry = VariableRegistry(path=tmp_path / "registry.json")
        registry.add_variable(
            canonical="distance",
            display="Distance",
            unit="km"
        )
        assert "distance" in registry.variables
        assert registry.variables["distance"]["display"] == "Distance"
        assert registry.variables["distance"]["count"] == 1

    def test_add_variable_with_aliases(self, tmp_path):
        """Adds variable with initial aliases."""
        registry = VariableRegistry(path=tmp_path / "registry.json")
        registry.add_variable(
            canonical="avg_heart_rate",
            display="Avg Heart Rate",
            unit="bpm",
            aliases=["avg_hr", "heart_rate"]
        )
        assert registry.get_canonical("avg_hr") == "avg_heart_rate"

    def test_add_alias_to_existing(self, tmp_path):
        """Adds alias to existing variable."""
        registry = VariableRegistry(path=tmp_path / "registry.json")
        registry.variables = {
            "avg_heart_rate": {"display": "Avg Heart Rate", "aliases": [], "unit": "bpm", "count": 1}
        }
        registry.add_alias("avg_heart_rate", "hr_avg")
        assert "hr_avg" in registry.variables["avg_heart_rate"]["aliases"]

    def test_increment_count(self, tmp_path):
        """Increments count when variable seen again."""
        registry = VariableRegistry(path=tmp_path / "registry.json")
        registry.variables = {
            "distance": {"display": "Distance", "aliases": [], "unit": "km", "count": 1}
        }
        registry.increment_count("distance")
        assert registry.variables["distance"]["count"] == 2


class TestRegistrySave:
    """Persisting registry to disk."""

    def test_save_creates_file(self, tmp_path):
        """Save writes registry to JSON file."""
        registry_path = tmp_path / "registry.json"
        registry = VariableRegistry(path=registry_path)
        registry.add_variable("distance", "Distance", "km")
        registry.save()
        
        assert registry_path.exists()
        saved = json.loads(registry_path.read_text())
        assert "distance" in saved

    def test_save_preserves_data(self, tmp_path):
        """Save/load round-trip preserves all data."""
        registry_path = tmp_path / "registry.json"
        
        # Create and save
        registry1 = VariableRegistry(path=registry_path)
        registry1.add_variable("distance", "Distance", "km", aliases=["dist"])
        registry1.save()
        
        # Load fresh
        registry2 = VariableRegistry(path=registry_path)
        assert registry2.variables["distance"]["aliases"] == ["dist"]
