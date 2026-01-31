import json
from datetime import datetime
from pathlib import Path

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test data directory
TEST_DATA_DIR = Path("/Users/jayminchang/Documents/projects/vokuAI/data/sessions")


@pytest.fixture(autouse=True)
def cleanup_test_sessions():
    """Clean up test sessions before and after each test."""
    yield
    # Clean up any test sessions created
    if TEST_DATA_DIR.exists():
        for file in TEST_DATA_DIR.glob("*.json"):
            # Only delete test sessions (those created during test runs)
            # You can add more sophisticated filtering if needed
            pass


class TestCreateSession:
    """Tests for POST /fitness/sessions"""

    def test_create_session_with_full_data(self):
        """Test creating session with all fields"""
        payload = {
            "workout_type": "Upper Body",
            "workout_date": "2026-01-28",
            "workout_time": "17:00",
            "variables": {
                "duration": 45,
                "avg_hr": 135,
                "rpe": 7
            }
        }
        
        response = client.post("/fitness/sessions", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["workout_type"] == "Upper Body"
        assert data["workout_date"] == "2026-01-28"
        assert data["workout_time"] == "17:00"
        assert data["variables"]["duration"] == 45
        assert data["variables"]["avg_hr"] == 135
        assert data["variables"]["rpe"] == 7
        assert "id" in data
        assert "created_at" in data

    def test_create_session_defaults_to_today(self):
        """Test that workout_date defaults to today if not provided"""
        payload = {
            "workout_type": "Zone 2 Row",
            "variables": {
                "duration": 30
            }
        }
        
        response = client.post("/fitness/sessions", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have workout_date (defaulted to today)
        assert "workout_date" in data
        assert data["workout_date"] == datetime.now().strftime("%Y-%m-%d")
        
        # Should have workout_time (defaulted to now)
        assert "workout_time" in data

    def test_create_session_validates_workout_type(self):
        """Test that workout_type is required"""
        payload = {
            "variables": {
                "duration": 30
            }
        }
        
        response = client.post("/fitness/sessions", json=payload)
        
        assert response.status_code == 422  # Validation error

    def test_create_session_validates_date_format(self):
        """Test that workout_date must be YYYY-MM-DD"""
        payload = {
            "workout_type": "Running",
            "workout_date": "01-28-2026",  # Wrong format
            "variables": {
                "duration": 30
            }
        }
        
        response = client.post("/fitness/sessions", json=payload)
        
        assert response.status_code == 422  # Validation error

    def test_create_session_validates_time_format(self):
        """Test that workout_time must be HH:MM"""
        payload = {
            "workout_type": "Running",
            "workout_time": "5:00 PM",  # Wrong format
            "variables": {
                "duration": 30
            }
        }
        
        response = client.post("/fitness/sessions", json=payload)
        
        assert response.status_code == 422  # Validation error


class TestGetSession:
    """Tests for GET /fitness/sessions/{id}"""

    def test_get_session_by_id(self):
        """Test retrieving a session by ID"""
        # First create a session
        payload = {
            "workout_type": "S&S",
            "variables": {
                "swings": 100,
                "getups": 6
            }
        }
        
        create_response = client.post("/fitness/sessions", json=payload)
        created = create_response.json()
        session_id = created["id"]
        
        # Now retrieve it
        response = client.get(f"/fitness/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["workout_type"] == "S&S"
        assert data["variables"]["swings"] == 100

    def test_get_nonexistent_session_returns_404(self):
        """Test that getting nonexistent session returns 404"""
        response = client.get("/fitness/sessions/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestListSessions:
    """Tests for GET /fitness/sessions"""

    def test_list_sessions_returns_array(self):
        """Test that listing sessions returns an array"""
        response = client.get("/fitness/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_sessions_respects_limit(self):
        """Test that limit parameter works"""
        # Create 3 sessions
        for i in range(3):
            payload = {
                "workout_type": f"Session {i}",
                "variables": {"duration": 30}
            }
            client.post("/fitness/sessions", json=payload)
        
        # Request only 2
        response = client.get("/fitness/sessions?limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    def test_list_sessions_sorts_newest_first(self):
        """Test that sessions are sorted by workout_date/time desc"""
        # Create sessions with different dates
        sessions = [
            {"workout_type": "Old", "workout_date": "2026-01-26", "workout_time": "10:00", "variables": {"duration": 30}},
            {"workout_type": "New", "workout_date": "2026-01-28", "workout_time": "15:00", "variables": {"duration": 30}},
            {"workout_type": "Middle", "workout_date": "2026-01-27", "workout_time": "12:00", "variables": {"duration": 30}},
        ]
        
        for session in sessions:
            client.post("/fitness/sessions", json=session)
        
        response = client.get("/fitness/sessions")
        data = response.json()
        
        # Should be sorted newest first
        if len(data) >= 3:
            # Check that the most recent sessions are first
            newest_sessions = data[:3]
            dates_times = [
                (s.get("workout_date", ""), s.get("workout_time", ""))
                for s in newest_sessions
            ]
            # Verify sorting (newest first)
            assert dates_times == sorted(dates_times, reverse=True)


class TestUpdateSession:
    """Tests for PUT /fitness/sessions/{id}"""

    def test_update_session_partial_fields(self):
        """Test updating only some fields"""
        # Create session
        payload = {
            "workout_type": "Running",
            "variables": {
                "duration": 30,
                "distance": 5
            }
        }
        
        create_response = client.post("/fitness/sessions", json=payload)
        created = create_response.json()
        session_id = created["id"]
        
        # Update only workout_type
        update_payload = {
            "workout_type": "Easy Run"
        }
        
        response = client.put(f"/fitness/sessions/{session_id}", json=update_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["workout_type"] == "Easy Run"
        # Variables should be unchanged
        assert data["variables"]["duration"] == 30
        assert data["variables"]["distance"] == 5
        # Should have updated_at
        assert "updated_at" in data

    def test_update_session_requires_at_least_one_field(self):
        """Test that update requires at least one field"""
        # Create session
        payload = {
            "workout_type": "Cycling",
            "variables": {"duration": 45}
        }
        
        create_response = client.post("/fitness/sessions", json=payload)
        created = create_response.json()
        session_id = created["id"]
        
        # Try to update with no fields
        response = client.put(f"/fitness/sessions/{session_id}", json={})
        
        assert response.status_code == 422  # Validation error

    def test_update_nonexistent_session_returns_404(self):
        """Test that updating nonexistent session returns 404"""
        update_payload = {
            "workout_type": "Test"
        }
        
        response = client.put("/fitness/sessions/nonexistent", json=update_payload)
        
        assert response.status_code == 404


class TestDeleteSession:
    """Tests for DELETE /fitness/sessions/{id}"""

    def test_delete_session(self):
        """Test deleting a session"""
        # Create session
        payload = {
            "workout_type": "Test Session",
            "variables": {"duration": 10}
        }
        
        create_response = client.post("/fitness/sessions", json=payload)
        created = create_response.json()
        session_id = created["id"]
        
        # Delete it
        response = client.delete(f"/fitness/sessions/{session_id}")
        
        assert response.status_code == 200
        assert "deleted" in response.json()["detail"].lower()
        
        # Verify it's gone
        get_response = client.get(f"/fitness/sessions/{session_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_session_returns_404(self):
        """Test that deleting nonexistent session returns 404"""
        response = client.delete("/fitness/sessions/nonexistent")
        
        assert response.status_code == 404
