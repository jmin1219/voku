from datetime import datetime
from typing import Any

from app.services.storage import (
    create_session,
    delete_session,
    get_session_by_id,
    list_sessions,
    update_session,
)
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

router = APIRouter()


class Session(BaseModel):
    """Canonical representation of a fitness session."""

    id: str
    created_at: datetime
    workout_date: str | None = None  # YYYY-MM-DD format
    workout_time: str | None = None  # HH:MM format
    workout_type: str | None = None
    variables: dict[str, Any]
    updated_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class SessionCreate(BaseModel):
    """Payload for creating a session."""

    workout_type: str = Field(..., min_length=1, max_length=100)
    variables: dict[str, Any] = Field(
        ..., description="Captured metrics for the session"
    )
    workout_date: str | None = Field(
        default=None,
        description="Date workout happened (YYYY-MM-DD), defaults to today",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    workout_time: str | None = Field(
        default=None,
        description="Time workout started (HH:MM), defaults to now",
        pattern=r"^\d{2}:\d{2}$"
    )


class SessionUpdate(BaseModel):
    """Payload for updating a session."""

    workout_type: str | None = Field(default=None, min_length=1, max_length=100)
    variables: dict[str, Any] | None = None
    workout_date: str | None = Field(
        default=None,
        description="Date workout happened (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    workout_time: str | None = Field(
        default=None,
        description="Time workout started (HH:MM)",
        pattern=r"^\d{2}:\d{2}$"
    )

    @model_validator(mode="after")
    def at_least_one_field(self) -> "SessionUpdate":
        """Ensure at least one field is supplied."""
        if all(
            field is None
            for field in [
                self.workout_type,
                self.variables,
                self.workout_date,
                self.workout_time,
            ]
        ):
            raise ValueError(
                "Provide at least one field: workout_type, variables, workout_date, or workout_time"
            )
        return self


class MessageResponse(BaseModel):
    """Generic message wrapper."""

    detail: str


@router.get("/sessions", response_model=list[Session])
def get_sessions(
    limit: int = Query(20, ge=1, le=200, description="Number of sessions to return"),
):
    """List recent fitness sessions, newest first by workout date/time."""
    return list_sessions(limit)


@router.get("/sessions/{session_id}", response_model=Session)
def get_session(session_id: str):
    """Retrieve an individual session by its ID."""
    session = get_session_by_id(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return session


@router.post("/sessions", response_model=Session, status_code=status.HTTP_201_CREATED)
def create_session_endpoint(payload: SessionCreate):
    """Create a new fitness session."""
    return create_session(
        workout_type=payload.workout_type,
        variables=payload.variables,
        workout_date=payload.workout_date,
        workout_time=payload.workout_time,
    )


@router.put("/sessions/{session_id}", response_model=Session)
def update_session_endpoint(session_id: str, payload: SessionUpdate):
    """Update an existing fitness session."""
    session = update_session(
        session_id,
        variables=payload.variables,
        workout_type=payload.workout_type,
        workout_date=payload.workout_date,
        workout_time=payload.workout_time,
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return session


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def delete_session_endpoint(session_id: str):
    """Delete a fitness session."""
    success = delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return MessageResponse(detail="Session deleted")
