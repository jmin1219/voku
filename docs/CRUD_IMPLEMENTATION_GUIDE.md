# Fitness CRUD Implementation Guide

> Technical hints for implementing GET/POST/PUT/DELETE endpoints. User codes the implementation.

**Date:** 2026-01-28  
**Goal:** Complete fitness domain CRUD to make v0.2 usable for daily logging without screenshots.

---

## Architecture Overview

**Current state:**
- `storage.py` has `save_session()` and `list_sessions()`
- Sessions stored as JSON files: `YYYY-MM-DD_HH-MM-SS_{id}.json`
- File naming enables chronological sorting
- Each session has: `id`, `created_at`, `variables` dict

**Target state:**
- Add 4 new functions to `storage.py`
- Add 4 new routes to `fitness.py`
- Frontend forms to create/edit sessions
- Full workflow: manual entry → save → edit → delete

---

## Backend: storage.py Functions

### 1. get_session_by_id(session_id: str) -> dict | None

**Purpose:** Retrieve a single session by its ID

**Hints:**
- Loop through all files in DATA_DIR
- Each filename contains the session ID (last 8 chars before .json)
- Read and parse JSON
- Return the session dict if found, None if not

**Edge cases:**
- What if DATA_DIR doesn't exist?
- What if no file contains that ID?

---

### 2. create_session(workout_type: str, variables: dict) -> dict

**Purpose:** Manually create a session without image upload

**Hints:**
- Similar to `save_session()` but takes explicit workout_type
- Generate new ID with `str(uuid4())[:8]`
- Create session dict with id, created_at, workout_type, variables
- Save to JSON file with timestamp naming convention
- Return the created session dict

**Differences from save_session:**
- Takes workout_type as parameter (not extracted from image)
- Returns full session dict (not just metadata)

---

### 3. update_session(session_id: str, workout_type: str, variables: dict) -> dict | None

**Purpose:** Edit an existing session's data

**Hints:**
- Find the file containing session_id (use get_session_by_id logic)
- Read existing session
- Update workout_type and variables
- Keep original id and created_at
- Add/update `updated_at` timestamp
- Write back to same file
- Return updated session dict

**Edge cases:**
- What if session doesn't exist?
- Should we validate that variables match known registry?

---

### 4. delete_session(session_id: str) -> bool

**Purpose:** Remove a session file

**Hints:**
- Find file containing session_id
- Use `os.remove()` to delete file
- Return True if deleted, False if not found

**Edge cases:**
- What if file doesn't exist?
- Should we log deletion for audit trail?

---

## Backend: fitness.py Routes

### 1. GET /fitness/sessions/{session_id}

**Purpose:** Fetch single session for viewing/editing

**FastAPI pattern:**
```python
@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    # Call storage function
    # Return session or 404 error
```

**Hints:**
- Import `HTTPException` from fastapi
- Return `HTTPException(status_code=404)` if session not found

---

### 2. POST /fitness/sessions

**Purpose:** Create new session from manual entry

**FastAPI pattern:**
```python
@router.post("/sessions")
def create_session(workout_type: str, variables: dict):
    # Call storage function
    # Return created session
```

**Hints:**
- Use Pydantic model for request body validation?
- Or keep it simple with plain dict?

---

### 3. PUT /fitness/sessions/{session_id}

**Purpose:** Update existing session

**FastAPI pattern:**
```python
@router.put("/sessions/{session_id}")
def update_session(session_id: str, workout_type: str, variables: dict):
    # Call storage function
    # Return updated session or 404
```

---

### 4. DELETE /fitness/sessions/{session_id}

**Purpose:** Delete session

**FastAPI pattern:**
```python
@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    # Call storage function
    # Return success message or 404
```

**Return format:** `{"deleted": True}` or similar

---

## Frontend: React Components

### 1. Manual Entry Form (New Component)

**Location:** `frontend/src/components/fitness/SessionForm.tsx`

**Props:**
- `mode: "create" | "edit"`
- `initialData?: Session` (for edit mode)
- `onSave: (data) => void`
- `onCancel: () => void`

**Form fields:**
- Workout type (text input or dropdown)
- Variables (dynamic fields based on registry)
- Each variable: canonical name, value, unit

**Hints:**
- Use shadcn Form components
- Fetch registry variables for autocomplete?
- Validate units match registry

---

### 2. Edit Modal (Integrate into History.tsx)

**Purpose:** Click row → open edit modal

**Pattern:**
- Add "Edit" button/icon to each row
- onClick → fetch session by ID
- Open SessionForm in modal with initialData
- onSave → call PUT endpoint, refresh list

**Hints:**
- Use shadcn Dialog component
- Store selected session in state
- Close modal after successful save

---

### 3. Delete Confirmation

**Pattern:**
- Add "Delete" button to rows
- Show confirmation dialog
- On confirm → call DELETE endpoint
- Refresh session list

**Hints:**
- Use shadcn AlertDialog for confirmation
- Destructive styling for delete button

---

## Testing Checklist

**Manual testing workflow:**

1. **Create:** Fill form → submit → verify appears in list
2. **View:** Click session → verify all data displays correctly  
3. **Edit:** Modify values → save → verify changes persist
4. **Delete:** Delete session → verify removed from list
5. **Edge cases:**
   - Try to edit non-existent ID (should 404)
   - Try to delete already-deleted session
   - Create session with empty variables
   - Special characters in workout type

**Unit tests (future):**
- Test each storage function
- Test each route with mock data
- Test error cases (404s, invalid input)

---

## Implementation Order

**Recommended sequence:**

1. **storage.py first** (backend logic)
   - get_session_by_id
   - create_session
   - update_session
   - delete_session
   - Test with Python REPL

2. **fitness.py routes** (API layer)
   - GET /sessions/{id}
   - POST /sessions
   - PUT /sessions/{id}
   - DELETE /sessions/{id}
   - Test with curl/Postman

3. **Frontend forms** (UI layer)
   - SessionForm component
   - Add to History page
   - Wire up API calls
   - Test full workflow

---

## Questions to Consider

1. **Validation:** Should we validate variables against registry before saving?
2. **Audit trail:** Should we keep deletion history or just remove files?
3. **Concurrency:** What if two edits happen simultaneously? (Unlikely for single user)
4. **File locking:** Do we need file locks for writes? (Probably not for MVP)

---

## Success Criteria

**v0.2 is complete when:**
- ✅ Can manually log tonight's S1 session without screenshot
- ✅ Can edit a session if I forgot to add a metric
- ✅ Can delete a duplicate or test session
- ✅ All operations persist correctly to JSON files
- ✅ Frontend flows feel natural and complete

**Time estimate:** ~3-4 hours (backend 1h, routes 30min, frontend 1.5-2h)

---

## References

- Existing code: `storage.py`, `fitness.py`
- FastAPI docs: https://fastapi.tiangolo.com/tutorial/path-params/
- shadcn Form: https://ui.shadcn.com/docs/components/form
- shadcn Dialog: https://ui.shadcn.com/docs/components/dialog
