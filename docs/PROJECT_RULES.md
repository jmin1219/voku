# Voku Project Rules

Ground rules for development. Reference these when making decisions.

---

## Process

### 1. Learn by building
Code every part myself. Claude guides through concepts, not copy-paste blocks. Understand each piece before moving on.

### 2. Scope discipline
New ideas mid-build get logged in STATE.md under "Deferred Ideas" and we keep moving. No pivots without completing current milestone.

### 3. Time-box exploration
Stuck >45 minutes? Surface it. Either solve it together or find a workaround. No silent spinning.

### 4. "Done" criteria first
Each step has explicit "done when" defined before starting. See STATE.md for current criteria.

### 5. Momentum over perfection
Working ugly version today beats theoretical elegant version next week. Refactor later. Ship first.

---

## Standards

### 6. TDD for core logic
Tests for demo-critical paths: extraction, storage, retrieval. Parser must have test coverage before moving to next phase.

### 7. Git hygiene
- Atomic commits with clear messages
- This is portfolio code — commit history is visible

### 8. Decision log
When choosing X over Y, note in STATE.md under "Decisions Made" with rationale.

---

## Documentation

### 9. State tracking
Update `STATE.md` at end of each session with current position, blockers, next steps.

### 10. Dual logging
Key insights also go to Jaymin_Brain vault. The project and thinking about the project both matter.

### 11. Public trail
Milestones → post on X (@ChangJaymin). Building in public creates evidence.

---

## What This Prevents

| Rule | Prevents |
|------|----------|
| Scope discipline | Endless pivots, no shipped code |
| "Done" criteria | Premature checkmarks, hidden bugs |
| Time-box | Hours lost to rabbit holes |
| TDD for core | Demo failures from untested edge cases |
| State tracking | Context loss between sessions |
