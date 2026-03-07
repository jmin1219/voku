---
created: 2026-03-07
updated: 2026-03-07
type: spec
status: active
---
# Voku Portfolio Completion Spec

> Single goal: Make Voku demo-ready for Fall 2026 co-op applications.
> Everything in this spec serves that goal. Nothing else ships.

---

## Current State (Mar 7)

| Metric | Value |
|--------|-------|
| Backend tests | 271 passing |
| Traces (seeded) | 869 across 8 domains |
| Semantic connections | 4,345 |
| Temporal connections | 758 |
| DBSCAN clusters | 34 |
| LOC | ~7,600 |
| Hours invested | ~120 |
| Phase 7 tasks | 7/9 complete |

**What works:** Chat with trace-based context assembly, streaming responses,
annotation extraction, temporal digest, resurfacing, phase space with clustering,
context markers, k-NN edges, retrieval glow, hover labels.

**What's missing:** Docker, deployment, environment-based API URL, README,
demo script, repo sanitization, resume update.

---

## Completion Tasks (ordered)

### Task 1: Environment-based API URL ✅
**Completed:** Mar 7. ~10 min.
**What changed:**
- Created `frontend/src/config.ts` — single source of truth for API_BASE
- Updated `Workspace.tsx`, `usePhaseSpace.ts`, `ContextMarker.tsx` to import from config
- Created `frontend/.env.example`
**Files:**
- `frontend/src/pages/Workspace.tsx` — line 17
- `frontend/src/hooks/usePhaseSpace.ts` — line 4
- `frontend/src/components/chat/ContextMarker.tsx` — line 3

**Changes:**
1. Create `frontend/src/config.ts`:
   ```ts
   export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";
   ```
2. Replace hardcoded URLs in all 3 files with import from config.
3. Add `VITE_API_BASE` to `.env.example`.

**Test:** `npm run build` succeeds. Dev still works on localhost.
**Time estimate:** 15 min.

---

### Task 2: Backend CORS for deployment ✅
**Completed:** Mar 7. ~5 min.
**What changed:**
- Added `cors_origins` field to `config.py`
- Updated `main.py`: CORS middleware always added, origins sourced from env
- Updated `backend/.env.example` with CORS_ORIGINS + ANTHROPIC_API_KEY

**Changes:**
- `backend/app/main.py`: Add production CORS config that reads allowed
  origins from env var `VOKU_CORS_ORIGINS` (comma-separated).
- `backend/app/config.py`: Add `cors_origins: str = ""` field.
- Keep dev fallback to localhost:5173.

**Test:** Backend starts with `ENVIRONMENT=production` and custom origins.
**Time estimate:** 10 min.

---

### Task 3: Dockerfile + docker-compose.yml ✅
**Completed:** Mar 7. ~25 min (including TS fixes).
**What changed:**
- Created `Dockerfile` — multi-stage (Node 20 build → Python 3.13 runtime)
- Created `docker-compose.yml` — single service, env from `.env`, persistent volume
- Created `.dockerignore`, `.env.example` (root)
- Updated `backend/app/main.py` — static file serving + SPA catch-all in production
- Updated `backend/requirements.txt` — added umap-learn, scikit-learn, anthropic
- Fixed TS build errors: removed unused imports (Workspace.tsx, ChatMessages.tsx), added JSX import (Markdown.tsx)
- Image bakes in BGE model (~420MB) + seeded voku.db (5.5MB, 869 traces)
- Container size: ~515MB memory at runtime

**Architecture:**
- Single `Dockerfile` with multi-stage build:
  - Stage 1: Node build (frontend → dist/)
  - Stage 2: Python runtime (backend + serve dist/ via FastAPI static mount)
- `docker-compose.yml` for single-command startup.
- Pre-seeded `voku.db` baked into the image (snapshot current 869-trace DB).

**Files to create:**
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `.env.example` (updated with all vars)

**Changes to existing files:**
- `backend/app/main.py`: Mount `frontend/dist` as static files when
  `ENVIRONMENT=production`. Serve index.html as catch-all for SPA routing.
- `frontend/vite.config.ts`: Set `base: '/'` explicitly.

**Environment variables (documented in .env.example):**
```
ENVIRONMENT=production
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
VOKU_PROVIDER=groq
VOKU_CORS_ORIGINS=
VITE_API_BASE=/api
```

**Acceptance criteria:**
1. `docker compose up --build` starts the full app on port 8000.
2. `http://localhost:8000` serves the frontend.
3. `http://localhost:8000/api/status` returns JSON.
4. Chat works (requires Anthropic key).
5. Phase space renders with seeded data.
6. Image size < 2GB.

**Test:** Full build + run on clean Docker environment.
**Time estimate:** 2-3 hours.

---

### Task 4: Deploy to Railway (or Render)
**Why:** Live URL for resume + README. Proves "I can deploy."

**Steps:**
1. Push Docker image or connect GitHub repo to Railway.
2. Set environment variables in Railway dashboard.
3. Verify deployed URL loads frontend + API.
4. Note: Chat requires Anthropic key — demo may be read-only
   (phase space + history viewable, chat disabled without key).

**Acceptance criteria:**
1. Public URL loads Voku frontend.
2. Phase space renders with seeded data.
3. `/api/status` returns healthy.
4. If no Anthropic key: chat shows graceful error, not crash.

**Graceful degradation (no API keys):**
- Chat: Show message "API key required for live chat. See demo video."
- Phase space: Works (pre-computed, no LLM needed).
- History: Works (reads from seeded DB).
- Digest: Fails gracefully (LLM-dependent).

**Time estimate:** 1-2 hours.

---

### Task 5: Repo sanitization + GitHub public
**Why:** Recruiter will look at GitHub within 30 seconds. Must be clean.

**Steps:**
1. Audit for secrets: grep for API keys, tokens, personal paths.
2. Add/update `.gitignore`: `*.db`, `.env`, `venv/`, `node_modules/`,
   `__pycache__/`, `backend/data/`, `.pytest_cache/`.
3. Remove `docs/private/` from tracking (if sensitive).
4. Squash or clean commit messages on feature branch.
5. Merge `feat/v2-trace-architecture` → `main`.
6. Push. Make repo public.
7. Pin on GitHub profile. Add topics: `llm`, `rag`, `knowledge-graph`,
   `fastapi`, `python`, `react`, `threejs`.

**Acceptance criteria:**
1. `git log --oneline` reads clean.
2. No secrets in history (or use BFG if needed).
3. Repo is public and pinned.

**Time estimate:** 1-2 hours.

---

### Task 6: README (employer narrative)
**Why:** This is the first thing a recruiter reads. It IS the pitch.

**Structure:**
```
# Voku — Transparent Thinking Environment for AI Agents

[One-paragraph pitch]
[Screenshot: phase space with clusters]
[Screenshot: chat with context markers]

## What It Does
[3 sentences max]

## Architecture
[Data model diagram or table]
[Stack badges]

## Key Technical Decisions
- Custom graph over external DB (why)
- Trace-based over proposition-based (why)
- Cosine + graph expansion retrieval (what it enables)
- Hierarchical DBSCAN clustering (how it works)

## What I Learned / What's Next
- Retrieval > write strategy (citing the bottleneck paper)
- BM25 + hybrid reranking as next step
- MemoryArena benchmark opportunity

## Run It
[Docker one-liner]
[Local dev setup]

## Stats
869 traces | 271 tests | 7,600 LOC | 120 hours
```

**Acceptance criteria:**
1. README renders well on GitHub.
2. Screenshots are current (from seeded 869-trace DB).
3. No personal/sensitive info.
4. Employer narrative matches career plan framing.

**Time estimate:** 2 hours.

---

### Task 7: Demo script + recording
**Why:** Recruiters won't run your Docker. They'll watch a 90-second video.

**Deliverable:** `docs/DEMO_SCRIPT.md` + screen recording (optional).

**Script structure (≤90 seconds):**
1. Open — populated phase space, 869 traces, visible clusters. (5s)
2. Ask a cross-session question: "How has my thinking about Voku evolved?"
   Watch context markers appear, retrieval glow in phase space. (15s)
3. Hover traces — see content, timestamps, domains. (10s)
4. Show cluster separation — career, academics, training, voku visible. (10s)
5. Trigger digest: "summarize my last month." Narrative response. (15s)
6. Quick scroll through history — multiple conversations, real data. (10s)
7. Close with thesis: "869 traces, 34 clusters, 4345 connections.
   The graph that emerges from daily use becomes the context layer
   any AI agent can query." (15s)

**Pre-tested queries (with fallbacks):**
- Primary: "How has my thinking about career direction evolved?"
- Fallback: "What patterns do you see in my recent conversations?"
- Digest: "Give me a digest of the last 30 days"

**Acceptance criteria:**
1. Script times to ≤90 seconds read aloud.
2. Every feature shown has working backend + frontend.
3. Queries pre-tested against seeded data.

**Time estimate:** 1.5 hours (script + rehearsal).

---

### Task 8: Resume update
**Why:** Resume is the delivery vehicle. Voku must be on it.

**Changes:**
- Add Voku as lead project (above APOLLO/Trivial Pursuit).
- Framing: "Temporal knowledge graph memory system for LLM agents.
  Custom graph architecture in Python, bge-base-en-v1.5 embeddings,
  cosine-similarity retrieval. 271 tests, FastAPI backend, 7,600 LOC."
- Add skills: sentence-transformers, graph architecture, LLM orchestration, Docker.
- Remove or minimize Trivial Pursuit.
- Add deployed URL.

**Time estimate:** 1 hour.

---

## Dependency Graph

```
Task 1 (env URL)  ──┐
Task 2 (CORS)     ──┼──► Task 3 (Docker) ──► Task 4 (Deploy)
                    │                              │
                    │         Task 5 (sanitize) ───┤
                    │                              │
                    └──────────────────────────────►├──► Task 6 (README)
                                                   │
                                                   ├──► Task 7 (Demo)
                                                   │
                                                   └──► Task 8 (Resume)
```

Tasks 1+2 are prerequisites for 3. Task 3 enables 4.
Tasks 5-8 can run in parallel after 4, but README needs screenshots
from the deployed/running app.

---

## Time Budget

| Task | Estimate | Cumulative |
|------|----------|------------|
| 1. Env URL | 15 min | 0:15 |
| 2. CORS | 10 min | 0:25 |
| 3. Docker | 2-3 hrs | 3:25 |
| 4. Deploy | 1-2 hrs | 5:25 |
| 5. Sanitize | 1-2 hrs | 7:25 |
| 6. README | 2 hrs | 9:25 |
| 7. Demo | 1.5 hrs | 10:55 |
| 8. Resume | 1 hr | 11:55 |
| **Buffer** | **3 hrs** | **~15 hrs** |

**Realistic total: 12-15 hours of focused work.**
At 3-4 hr/day on project days, that's ~4-5 sessions.

---

## Schedule Integration

| Window | Tasks | Gate |
|--------|-------|------|
| Sat Mar 7 (today) | Tasks 1+2, start Task 3 | Frontend builds with env URL |
| After midterm (Mar 13-14) | Finish Task 3, Task 4, Task 5 | Docker runs, deployed URL works |
| Mar 15-22 | Tasks 6+7+8 | README on GitHub, demo scripted |
| Mar 23-31 | Polish, rehearse, buffer | Portfolio complete |

**Hard constraint:** CS5008 midterm Mar 12, CS5004 Phase 1 due Mar 16.
Voku work fits around these — not instead of them.

---

## Agentic Development Protocol

When Jaymin says "let's work on Voku" or triggers a task from this spec:

1. **Read this spec first.** Check which task is next in the dependency graph.
2. **Read the specific task section** for acceptance criteria and file list.
3. **Implement in mentor mode:** Explain what needs to change and why →
   Jaymin codes (or Claude codes if Jaymin delegates) → verify against
   acceptance criteria.
4. **Test before marking done.** Run the acceptance criteria literally.
5. **Update this spec** when a task completes:
   - Add ✅ to the task header
   - Log actual time vs estimate
   - Note any issues for the next task

### What Claude Does vs What Jaymin Does

| Claude does | Jaymin does |
|-------------|------------|
| Write config files, Dockerfiles, .env templates | Review and approve |
| Draft README content | Edit voice and framing |
| Generate demo script | Rehearse and record |
| Update spec with completion status | Decide priorities if schedule shifts |
| Flag blockers and propose solutions | Make final calls on tradeoffs |

### Code Changes — Claude's Protocol

For each file change:
1. State what file, what change, why.
2. Show the change (or make it directly if delegated).
3. Verify: does it build? Does it pass tests? Does it meet acceptance criteria?
4. If it breaks something, fix it before moving on.

---

## Out of Scope (Do NOT touch)

- New features (BM25, hybrid reranking, resource drop UI)
- Refactoring existing working code
- Frontend redesign
- Performance optimization
- v1 code cleanup
- MCP server changes
- Changing the data model
- Blog post (separate task, post-portfolio)

---

## Done Criteria (Portfolio Complete)

All of these must be true:

- [ ] `docker compose up` starts Voku on a clean machine
- [ ] Public URL loads frontend with seeded data
- [ ] Phase space shows 34+ clusters across 8 domains
- [ ] Chat works with Anthropic key (graceful error without)
- [ ] GitHub repo is public, pinned, with clean README
- [ ] README has screenshots, architecture, employer narrative
- [ ] Demo script exists and queries are pre-tested
- [ ] Resume lists Voku with deployed URL and stats
- [ ] No secrets in git history
