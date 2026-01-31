"""Tests for Registry Router endpoints."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestListVariables:
    """GET /registry/variables - list all variables."""
    
    def test_list_empty_registry(self, tmp_path, monkeypatch):
        """Returns empty list when registry is empty."""
        # Point registry to empty temp file
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", tmp_path / "test_registry.json")
        
        response = client.get("/registry/variables")
        assert response.status_code == 200
        data = response.json()
        assert data["variables"] == {}
        assert data["count"] == 0
    
    def test_list_populated_registry(self, tmp_path, monkeypatch):
        """Returns all variables when registry has data."""
        # Create test registry
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({
            "avg_heart_rate": {
                "display": "Avg Heart Rate",
                "aliases": ["avg_hr"],
                "unit": "bpm",
                "count": 5
            },
            "distance": {
                "display": "Distance",
                "aliases": [],
                "unit": "km",
                "count": 3
            }
        }))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.get("/registry/variables")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert "avg_heart_rate" in data["variables"]
        assert "distance" in data["variables"]


class TestGetVariable:
    """GET /registry/variables/{canonical} - get specific variable."""
    
    def test_get_existing_variable(self, tmp_path, monkeypatch):
        """Returns variable data when it exists."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({
            "avg_heart_rate": {
                "display": "Avg Heart Rate",
                "aliases": ["avg_hr"],
                "unit": "bpm",
                "count": 5
            }
        }))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.get("/registry/variables/avg_heart_rate")
        assert response.status_code == 200
        data = response.json()
        assert data["canonical"] == "avg_heart_rate"
        assert data["display"] == "Avg Heart Rate"
        assert data["aliases"] == ["avg_hr"]
        assert data["unit"] == "bpm"
        assert data["count"] == 5
    
    def test_get_nonexistent_variable(self, tmp_path, monkeypatch):
        """Returns 404 when variable doesn't exist."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({}))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.get("/registry/variables/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCreateVariable:
    """POST /registry/variables - create new variable."""
    
    def test_create_valid_variable(self, tmp_path, monkeypatch):
        """Creates variable successfully."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({}))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.post("/registry/variables", json={
            "canonical": "distance",
            "display": "Distance",
            "unit": "km",
            "aliases": []
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "created successfully" in data["message"]
        assert data["canonical"] == "distance"
        
        # Verify it was saved
        saved = json.loads(test_registry.read_text())
        assert "distance" in saved
    
    def test_create_with_aliases(self, tmp_path, monkeypatch):
        """Creates variable with multiple aliases."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({}))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.post("/registry/variables", json={
            "canonical": "avg_heart_rate",
            "display": "Avg Heart Rate",
            "unit": "bpm",
            "aliases": ["avg_hr", "heart_rate_avg"]
        })
        
        assert response.status_code == 201
        
        # Verify aliases saved
        saved = json.loads(test_registry.read_text())
        assert saved["avg_heart_rate"]["aliases"] == ["avg_hr", "heart_rate_avg"]
    
    def test_create_duplicate_canonical(self, tmp_path, monkeypatch):
        """Returns 400 when canonical name already exists."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({
            "distance": {"display": "Distance", "aliases": [], "unit": "km", "count": 1}
        }))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.post("/registry/variables", json={
            "canonical": "distance",
            "display": "Distance 2",
            "unit": "mi"
        })
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_create_with_conflicting_alias(self, tmp_path, monkeypatch):
        """Returns 400 when alias conflicts with existing variable."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({
            "avg_heart_rate": {
                "display": "Avg Heart Rate",
                "aliases": ["avg_hr"],
                "unit": "bpm",
                "count": 1
            }
        }))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.post("/registry/variables", json={
            "canonical": "heart_rate",
            "display": "Heart Rate",
            "unit": "bpm",
            "aliases": ["avg_hr"]  # Conflicts with existing alias
        })
        
        assert response.status_code == 400
        assert "conflicts" in response.json()["detail"]
    
    def test_create_invalid_canonical_uppercase(self, tmp_path, monkeypatch):
        """Returns 422 when canonical has uppercase letters."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({}))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.post("/registry/variables", json={
            "canonical": "AvgHeartRate",  # Invalid: uppercase
            "display": "Avg Heart Rate",
            "unit": "bpm"
        })
        
        assert response.status_code == 422
    
    def test_create_invalid_canonical_special_chars(self, tmp_path, monkeypatch):
        """Returns 422 when canonical has invalid special characters."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({}))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.post("/registry/variables", json={
            "canonical": "avg@heart!rate",  # Invalid: special chars
            "display": "Avg Heart Rate",
            "unit": "bpm"
        })
        
        assert response.status_code == 422


class TestAddAlias:
    """POST /registry/variables/{canonical}/aliases - add alias to variable."""
    
    def test_add_alias_to_existing_variable(self, tmp_path, monkeypatch):
        """Adds alias successfully."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({
            "avg_heart_rate": {
                "display": "Avg Heart Rate",
                "aliases": ["avg_hr"],
                "unit": "bpm",
                "count": 1
            }
        }))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.post("/registry/variables/avg_heart_rate/aliases", json={
            "alias": "heart_rate_avg"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "added" in data["message"]
        
        # Verify alias was added
        saved = json.loads(test_registry.read_text())
        assert "heart_rate_avg" in saved["avg_heart_rate"]["aliases"]
    
    def test_add_alias_to_nonexistent_variable(self, tmp_path, monkeypatch):
        """Returns 404 when variable doesn't exist."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({}))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.post("/registry/variables/nonexistent/aliases", json={
            "alias": "some_alias"
        })
        
        assert response.status_code == 404
    
    def test_add_duplicate_alias_same_variable(self, tmp_path, monkeypatch):
        """Returns 400 when alias already mapped to same variable."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({
            "avg_heart_rate": {
                "display": "Avg Heart Rate",
                "aliases": ["avg_hr"],
                "unit": "bpm",
                "count": 1
            }
        }))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.post("/registry/variables/avg_heart_rate/aliases", json={
            "alias": "avg_hr"  # Already exists
        })
        
        assert response.status_code == 400
        assert "already mapped" in response.json()["detail"]
    
    def test_add_alias_conflicts_with_other_variable(self, tmp_path, monkeypatch):
        """Returns 400 when alias already mapped to different variable."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({
            "avg_heart_rate": {
                "display": "Avg Heart Rate",
                "aliases": ["avg_hr"],
                "unit": "bpm",
                "count": 1
            },
            "distance": {
                "display": "Distance",
                "aliases": ["dist"],
                "unit": "km",
                "count": 1
            }
        }))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.post("/registry/variables/distance/aliases", json={
            "alias": "avg_hr"  # Conflicts with avg_heart_rate
        })
        
        assert response.status_code == 400
        assert "already mapped to" in response.json()["detail"]


class TestDeleteVariable:
    """DELETE /registry/variables/{canonical} - delete variable."""
    
    def test_delete_existing_variable(self, tmp_path, monkeypatch):
        """Deletes variable successfully."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({
            "distance": {
                "display": "Distance",
                "aliases": [],
                "unit": "km",
                "count": 1
            }
        }))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.delete("/registry/variables/distance")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        
        # Verify it was removed
        saved = json.loads(test_registry.read_text())
        assert "distance" not in saved
    
    def test_delete_nonexistent_variable(self, tmp_path, monkeypatch):
        """Returns 404 when variable doesn't exist."""
        test_registry = tmp_path / "test_registry.json"
        test_registry.write_text(json.dumps({}))
        
        from app.routers import registry as registry_module
        monkeypatch.setattr(registry_module, "REGISTRY_PATH", test_registry)
        
        response = client.delete("/registry/variables/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
