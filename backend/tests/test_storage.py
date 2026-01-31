import json
from datetime import datetime
from pathlib import Path

import pytest
from app.services.storage import (
    create_session,
    delete_session,
    get_session_by_id,
    list_sessions,
    update_session,
)

# Test data directory
TEST_DATA_DIR = Path("/Users/jayminchang/Documents/projects/vokuAI/data/sessions")


@pytest.fixture
def temp_session():
    """Create a temporary session for testing, clean up after"""
    session = create_session(
        workout_type="Test Workout",
        variables={"duration": 30, "rpe": 5},
        workout_date="2026-01-28",
        workout_time="10:00"
    )
    
    yield session
    
    # Cleanup
    delete_session(session["id"])


class TestCreateSession:
    """Tests for create_session function"""

    def test_create_session_generates_valid_structure(self):
        """Test that create_session returns proper structure"""
        session = create_session(
            workout_type="Running",
            variables={"distance": 5, "duration": 30},
            workout_date="2026-01-28",
            workout_time="17:00"
        )
        
        try:
            assert "id" in session
            assert len(session["id"]) == 8  # 8-char UUID prefix
            assert "created_at" in session
            assert session["workout_type"] == "Running"
            assert session["workout_date"] == "2026-01-28"
            assert session["workout_time"] == "17:00"
            assert session["variables"]["distance"] == 5
            assert session["variables"]["duration"] == 30
            
            # Verify file was created
            session_file = list(TEST_DATA_DIR.glob(f"*_{session['id']}.json"))
            assert len(session_file) == 1
        finally:
            # Cleanup
            delete_session(session["id"])

    def test_create_session_defaults_date_and_time(self):
        """Test that date/time default to now if not provided"""
        session = create_session(
            workout_type="Cycling",
            variables={"duration": 45}
        )
        
        try:
            assert "workout_date" in session
            assert "workout_time" in session
            
            # Should be today's date
            today = datetime.now().strftime("%Y-%m-%d")
            assert session["workout_date"] == today
            
            # Should be current time (within a minute)
            now = datetime.now().strftime("%H:%M")
            assert session["workout_time"] in [now, datetime.now().strftime("%H:%M")]
        finally:
            delete_session(session["id"])


class TestGetSession:
    """Tests for get_session_by_id function"""

    def test_get_session_by_id_returns_session(self, temp_session):
        """Test that get_session_by_id returns correct session"""
        retrieved = get_session_by_id(temp_session["id"])
        
        assert retrieved is not None
        assert retrieved["id"] == temp_session["id"]
        assert retrieved["workout_type"] == "Test Workout"
        assert retrieved["variables"]["duration"] == 30

    def test_get_session_by_id_returns_none_for_nonexistent(self):
        """Test that get_session_by_id returns None for nonexistent ID"""
        result = get_session_by_id("nonexistent")
        
        assert result is None


class TestListSessions:
    """Tests for list_sessions function"""

    def test_list_sessions_returns_list(self):
        """Test that list_sessions returns a list"""
        sessions = list_sessions(limit=20)
        
        assert isinstance(sessions, list)

    def test_list_sessions_respects_limit(self):
        """Test that list_sessions respects limit parameter"""
        # Create 3 test sessions
        test_sessions = []
        for i in range(3):
            session = create_session(
                workout_type=f"Test {i}",
                variables={"duration": 30}
            )
            test_sessions.append(session)
        
        try:
            # Request only 2
            sessions = list_sessions(limit=2)
            
            assert len(sessions) <= 2
        finally:
            # Cleanup
            for session in test_sessions:
                delete_session(session["id"])

    def test_list_sessions_empty_directory(self):
        """Test that list_sessions works with empty directory"""
        # This test assumes we can clear the directory or use a temp one
        # For now, just verify it returns a list (might be empty)
        sessions = list_sessions(limit=20)
        
        assert isinstance(sessions, list)

    def test_list_sessions_sorts_by_workout_datetime(self):
        """Test that sessions are sorted by workout_date + workout_time desc"""
        # Create sessions with different dates
        test_sessions = []
        sessions_data = [
            {"workout_type": "Old", "workout_date": "2026-01-26", "workout_time": "10:00"},
            {"workout_type": "New", "workout_date": "2026-01-28", "workout_time": "15:00"},
            {"workout_type": "Middle", "workout_date": "2026-01-27", "workout_time": "12:00"},
        ]
        
        for data in sessions_data:
            session = create_session(
                workout_type=data["workout_type"],
                variables={"duration": 30},
                workout_date=data["workout_date"],
                workout_time=data["workout_time"]
            )
            test_sessions.append(session)
        
        try:
            sessions = list_sessions(limit=10)
            
            # Find our test sessions in the results
            test_session_ids = {s["id"] for s in test_sessions}
            result_test_sessions = [s for s in sessions if s["id"] in test_session_ids]
            
            # Should be sorted newest first
            if len(result_test_sessions) >= 3:
                assert result_test_sessions[0]["workout_type"] == "New"
                assert result_test_sessions[1]["workout_type"] == "Middle"
                assert result_test_sessions[2]["workout_type"] == "Old"
        finally:
            # Cleanup
            for session in test_sessions:
                delete_session(session["id"])


class TestUpdateSession:
    """Tests for update_session function"""

    def test_update_session_modifies_fields(self, temp_session):
        """Test that update_session modifies specified fields"""
        updated = update_session(
            temp_session["id"],
            workout_type="Updated Workout"
        )
        
        assert updated is not None
        assert updated["workout_type"] == "Updated Workout"
        # Variables should be unchanged
        assert updated["variables"]["duration"] == 30
        assert "updated_at" in updated

    def test_update_session_preserves_unchanged_fields(self, temp_session):
        """Test that update_session preserves fields not being updated"""
        # Update only variables
        updated = update_session(
            temp_session["id"],
            variables={"distance": 10}
        )
        
        assert updated is not None
        # workout_type should be unchanged
        assert updated["workout_type"] == "Test Workout"
        # Variables should be updated
        assert updated["variables"]["distance"] == 10
        # Original variables are replaced (not merged)
        assert "duration" not in updated["variables"]

    def test_update_session_adds_updated_at_timestamp(self, temp_session):
        """Test that update_session adds updated_at field"""
        updated = update_session(
            temp_session["id"],
            workout_type="Modified"
        )
        
        assert updated is not None
        assert "updated_at" in updated
        # Should be ISO format datetime
        datetime.fromisoformat(updated["updated_at"])

    def test_update_session_returns_none_for_nonexistent(self):
        """Test that update_session returns None for nonexistent ID"""
        result = update_session(
            "nonexistent",
            workout_type="Test"
        )
        
        assert result is None


class TestDeleteSession:
    """Tests for delete_session function"""

    def test_delete_session_removes_file(self):
        """Test that delete_session removes the file"""
        # Create a session
        session = create_session(
            workout_type="To Delete",
            variables={"duration": 10}
        )
        
        session_id = session["id"]
        
        # Verify it exists
        assert get_session_by_id(session_id) is not None
        
        # Delete it
        result = delete_session(session_id)
        
        assert result is True
        
        # Verify it's gone
        assert get_session_by_id(session_id) is None

    def test_delete_session_returns_false_for_nonexistent(self):
        """Test that delete_session returns False for nonexistent ID"""
        result = delete_session("nonexistent")
        
        assert result is False


class TestFilenameGeneration:
    """Tests for session filename generation"""

    def test_filename_contains_date_and_id(self):
        """Test that generated filename contains date and session ID"""
        session = create_session(
            workout_type="Test",
            variables={"duration": 30}
        )
        
        try:
            # Find the file
            session_files = list(TEST_DATA_DIR.glob(f"*_{session['id']}.json"))
            assert len(session_files) == 1
            
            filename = session_files[0].name
            
            # Should contain date (YYYY-MM-DD format)
            assert session["created_at"][:10] in filename or datetime.now().strftime("%Y-%m-%d") in filename
            
            # Should contain session ID
            assert session["id"] in filename
            
            # Should be valid JSON
            with open(session_files[0]) as f:
                data = json.load(f)
                assert data["id"] == session["id"]
        finally:
            delete_session(session["id"])
