# CLAUDE-CODE-TASK: Deploy-Ready Prep

**Goal:** Make Voku deployable to any Docker-based hosting platform (Render, Railway, Fly.io) with a single `docker compose up --build`. Empty DB — visitors start fresh. Then swap the README with the new version.

**Branch:** Work on `main`. Commit atomically after each task.

**IMPORTANT:** Run `pytest` in `backend/` after any backend changes to verify 271 tests still pass. Run frontend build (`cd frontend && NODE_ENV=production npm run build`) after any frontend changes.

---

## Task 1: Git Cleanup

1. Add to `.gitignore`:
   ```
   # Dev screenshots
   phase-space-*.png
   
   # Playwright MCP logs
   .playwright-mcp/
   ```

2. Delete all `phase-space-*.png` files from repo root (they are untracked dev artifacts).

3. Stage and commit ALL current uncommitted changes (modified frontend + backend files + new untracked components like AnnotationBadges.tsx, NodeHoverCard.tsx, ParticleFlow.tsx, RetrievalTendrils.tsx, frontend/CLAUDE.md) as a single commit:
   ```
   feat: frontend polish — phase space improvements, design tokens, annotation badges
   ```

---

## Task 2: Rate Limiting on Chat & Digest

Add simple IP-based rate limiting to prevent API credit abuse. No Redis — use in-memory dict with TTL cleanup.

**Create `backend/app/middleware/__init__.py`:** empty file.

**Create `backend/app/middleware/rate_limit.py`:**

```python
"""Simple in-memory IP-based rate limiter. No external dependencies."""
import time
from collections import defaultdict
from fastapi import Request, HTTPException


class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request):
        ip = self._get_client_ip(request)
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]
        if len(self._requests[ip]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per hour.",
            )
        self._requests[ip].append(now)


chat_limiter = RateLimiter(max_requests=30, window_seconds=3600)
```

**Wire into `backend/app/routes/chat.py`:**
- Add import: `from fastapi import Request` (may already be imported from fastapi)
- Add import: `from app.middleware.rate_limit import chat_limiter`
- Add `request: Request` as first parameter to `async def chat(request: Request, data: ChatRequest):`
  - NOTE: rename the existing `request` parameter to `data` or `payload` to avoid collision
- Add as first line in the function body: `chat_limiter.check(request)`

**Wire into `backend/app/routes/digest.py`:**
- Same pattern — add rate limiter check at the top of the digest endpoint.

**Run tests:** `cd backend && source venv/bin/activate && pytest` — all 271 should pass.

**Commit:** `feat: add IP-based rate limiting to chat and digest endpoints`

---

## Task 3: Startup Logging

In `backend/app/main.py` inside the lifespan context manager, after the db_path setup, add:

```python
import logging
logger = logging.getLogger("voku")
logging.basicConfig(level=logging.INFO)
logger.info("Voku starting up...")
logger.info(f"Database: {db_path}")
logger.info(f"Provider: {settings.voku_provider}")
logger.info(f"Environment: {settings.environment}")

from app.dependencies import embedder
logger.info(f"Embedding model loaded: {embedder.model_name} ({embedder.dimensions}d)")
```

**Commit:** `chore: add startup logging for deployment diagnostics`

---

## Task 4: Frontend Empty State

When the DB is empty (0 traces), the app must not break.

**Verify these work correctly with 0 traces (empty DB):**
1. `GET /api/history` returns `[]` — chat panel shows empty state, not an error
2. `GET /api/phase-space` with 0 traces — returns valid response, doesn't crash
3. Chat input is immediately usable — type a message, get a streamed response

**In `frontend/src/components/phase-space/PhaseSpaceScene.tsx`:**
- If `data.traces` is empty/undefined/length 0, render a centered message instead of the Three.js canvas:
  ```
  "Start a conversation to see your knowledge graph emerge"
  ```
  Style it to match the existing design tokens (use var(--voku-text-muted) or similar).

**Test by temporarily using an empty DB:**
```bash
cd backend
mv data/voku.db data/voku.db.bak
# Start the app, verify empty state works
# Then restore: mv data/voku.db.bak data/voku.db
```

**Commit:** `fix: graceful empty state for fresh deployments`

---

## Task 5: Replace README

1. Copy `README_NEW.md` to `README.md` (overwrite).
2. Delete `README_NEW.md`.
3. Verify the README renders correctly (check markdown formatting).

**Commit:** `docs: README rewrite — architecture, design decisions, honest framing`

---

## Task 6: Docker Build Verification

**Build and test:**
```bash
cd /Users/jayminchang/Documents/projects/voku

# Make sure .env exists at project root with API keys
cp .env.example .env
# Edit .env: add ANTHROPIC_API_KEY and GROQ_API_KEY

docker compose build
docker compose up
```

**Test these endpoints:**
1. `http://localhost:8000/health` → `{"status": "healthy"}`
2. `http://localhost:8000/` → serves the React SPA
3. `http://localhost:8000/api/status` → `{"status": "ok", ...}`
4. `http://localhost:8000/api/history` → `[]`
5. Open the SPA in browser, type a message, verify streaming response works

**If the Docker build fails, fix it.** Common issues:
- `frontend/package-lock.json` out of sync → run `cd frontend && NODE_ENV=development npm install` first
- Tailwind v4 build issues
- Missing Python dependencies

**Commit any fixes as:** `fix: Docker build compatibility`

---

## Task 7: Final Cleanup

1. Delete `CLAUDE-CODE-TASK.md` from repo root
2. Delete `docs/RECORDING_SCRIPT.md` from repo (keep it local only — add to .gitignore or just remove)
3. Ensure working tree is clean
4. Push to origin: `git push origin main`

**Commit:** `chore: deploy-ready cleanup`

---

## Environment Notes
- Node: needs 18+ (check with `node -v`)
- Python: 3.13 in `backend/venv`
- Docker: must be running
- `NODE_ENV=production` may be in ~/.zshrc — prefix `NODE_ENV=development` for `npm install`
- API keys: in `backend/.env` (local dev) and root `.env` (Docker)

## What NOT to change
- Don't modify the core retrieval pipeline, annotation extraction, or trace storage logic
- Don't add authentication
- Don't touch test files unless fixing a test that breaks from rate limiting changes
- Keep all 271 tests passing
