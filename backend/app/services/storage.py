# backend/app/services/storage.py
import json
from datetime import datetime
from pathlib import Path
from typing import Tuple
from uuid import uuid4

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "sessions"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _generate_session_metadata() -> Tuple[str, datetime, str]:
    """Return (session_id, created_at, filename)."""
    session_id = str(uuid4())[:8]
    created_at = datetime.now()
    filename = f"{created_at.strftime('%Y-%m-%d_%H-%M-%S')}_{session_id}.json"
    return session_id, created_at, filename


def _write_session_file(session: dict, filename: str) -> Path:
    _ensure_data_dir()
    filepath = DATA_DIR / filename
    with open(filepath, "w") as f:
        json.dump(session, f, indent=2)
    return filepath


def save_session(variables: dict) -> dict:
    """Save extraction to JSON file. Returns metadata."""
    session_id, created_at, filename = _generate_session_metadata()
    session = {
        "id": session_id,
        "created_at": created_at.isoformat(),
        "variables": variables,
    }
    filepath = _write_session_file(session, filename)
    return {"id": session_id, "logged_to": str(filepath)}


def create_session(
    workout_type: str, 
    variables: dict,
    workout_date: str | None = None,
    workout_time: str | None = None,
) -> dict:
    """Create a new session with specified workout type and variables.
    
    Args:
        workout_type: Type of workout (e.g., "Upper Body")
        variables: Metrics collected
        workout_date: Date workout happened (YYYY-MM-DD), defaults to today
        workout_time: Time workout started (HH:MM), defaults to now
    """
    session_id, created_at, filename = _generate_session_metadata()
    
    # Default workout_date and workout_time to created_at if not provided
    if workout_date is None:
        workout_date = created_at.strftime('%Y-%m-%d')
    if workout_time is None:
        workout_time = created_at.strftime('%H:%M')
    
    session = {
        "id": session_id,
        "created_at": created_at.isoformat(),
        "workout_date": workout_date,
        "workout_time": workout_time,
        "workout_type": workout_type,
        "variables": variables,
    }
    _write_session_file(session, filename)
    return session


def update_session(
    session_id: str,
    variables: dict | None = None,
    workout_type: str | None = None,
    workout_date: str | None = None,
    workout_time: str | None = None,
) -> dict | None:
    """Update an existing session's fields.
    
    Args:
        session_id: Session ID to update
        variables: New variables dict (optional)
        workout_type: New workout type (optional)
        workout_date: New workout date in YYYY-MM-DD format (optional)
        workout_time: New workout time in HH:MM format (optional)
    """
    for filepath in DATA_DIR.iterdir():
        file_id = filepath.name.split("_")[-1].split(".")[0]
        if file_id == session_id:
            with filepath.open() as f:
                session = json.load(f)
            
            # Update provided fields only
            if variables is not None:
                session["variables"] = variables
            if workout_type is not None:
                session["workout_type"] = workout_type
            if workout_date is not None:
                session["workout_date"] = workout_date
            if workout_time is not None:
                session["workout_time"] = workout_time
            
            # Add updated_at timestamp
            session["updated_at"] = datetime.now().isoformat()
            
            # Write back to file
            with filepath.open("w") as f:
                json.dump(session, f, indent=2)
            return session
    return None


def list_sessions(limit: int = 20) -> list[dict]:
    """List recent sessions, newest first by workout date/time."""
    if not DATA_DIR.exists():
        return []

    files = list(DATA_DIR.iterdir())
    sessions = []

    for filepath in files:
        with filepath.open() as f:
            session = json.load(f)
            sessions.append(session)

    # Sort by workout_date + workout_time if available, otherwise created_at
    def sort_key(session: dict) -> str:
        if "workout_date" in session and "workout_time" in session:
            return f"{session['workout_date']} {session['workout_time']}"
        return session.get("created_at", "")
    
    sessions.sort(key=sort_key, reverse=True)
    return sessions[:limit]


def get_session_by_id(session_id: str) -> dict | None:
    """Retrieve a session by its ID."""
    if not DATA_DIR.exists():
        return None

    for filepath in DATA_DIR.iterdir():
        file_id = filepath.name.split("_")[-1].split(".")[0]
        if file_id == session_id:
            with filepath.open() as f:
                session = json.load(f)
                return session

    return None


def delete_session(session_id: str) -> bool:
    """Delete a session by its ID. Returns True if deleted, False if not found."""
    if not DATA_DIR.exists():
        return False

    for filepath in DATA_DIR.iterdir():
        file_id = filepath.name.split("_")[-1].split(".")[0]
        if file_id == session_id:
            filepath.unlink()
            return True

    return False
