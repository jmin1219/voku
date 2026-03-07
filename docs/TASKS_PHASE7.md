# Phase 7: Temporal Digest + Demo — Task Breakdown

**Created:** 2026-03-01
**Revised:** 2026-03-02 (real-data strategy replaces synthetic persona)
**SPEC ref:** § Build Sequence Phase 7, § Demo Narrative
**Test file prefix:** `test_phase7_` (backend), visual verification (frontend)

---

## Overview

Phase 7 has three goals:
1. **Content.** The phase space needs 200+ traces with real thematic structure to demonstrate clustering, contradiction, temporal evolution. Without this, the demo is a blob.
2. **Temporal digest.** The third surface — AI-synthesized narrative from the trace graph. "What have I been thinking about this month?" Stored as system traces, themselves retrievable.
3. **Demo readiness.** Deployment, visual polish, the narrative walkthrough.

**Strategy change (Mar 1):** Synthetic persona data (Mina) tested and failed — 200 traces with one character's thinking collapsed into 1 cluster because the content was too semantically coherent. Real multi-domain conversations produce better thematic separation naturally. Content now accumulates through daily Voku use across career, academics, training, and personal thinking.

Dependency order: Content accumulates organically (ongoing), code tasks are independent of content volume, demo polish once data is sufficient.

---

## Group A: Real Data Accumulation + DB Prep

### Task 7.1: Clean database + daily use protocol ✅

**What:** Wipe Mina seed data, start fresh v2 database, establish daily Voku usage as the content strategy. No script — this is operational.

**Steps:**
1. Delete or reset `backend/data/voku.db` (wipe v2 tables: traces, annotations, connections, resources, embeddings)
2. Delete `scripts/mina_arc.py` and `scripts/seed_mina.py` — synthetic strategy abandoned
3. Keep `scripts/seed_v2.py` as minimal seed for dev testing
4. Begin routing real thinking through Voku: spring break planning, CS5004 project, training decisions, career strategy, brain dumps

**Usage targets for demo-ready data:**
- 200+ traces across 2-3 weeks of daily use
- 5+ thematic domains (career/voku, academics, training, personal, technical)
- Natural contradictions/evolutions emerge from real thinking over time
- Cross-session references happen organically when revisiting topics

**Acceptance criteria:**
1. Database is clean — no Mina data
2. Mina scripts deleted from repo
3. First real conversation through Voku completed
4. Phase space renders (even if sparse initially)

**Gate:** After 1 week of daily use (~50-100 traces), phase space should show emerging cluster separation. If it doesn't, investigate clustering params before adding more data.

---

### Task 7.2: Fix annotation extraction (silent failure) ✅

**What:** Background annotation extraction runs after each chat message but produces 0 annotations. Groq API key is present. This is blocking the richness of the trace graph — without annotations, contradiction detection, pattern detection, and intention boost all have nothing to work with.

**Depends on:** Clean database (Task 7.1) — easier to debug with fresh data

**Investigation path:**
1. Check Groq API key validity (test with direct API call)
2. Check `background.py` — is the BackgroundTask actually firing?
3. Check `annotation.py` — is the LLM prompt returning parseable results?
4. Check storage — are annotations being written to DB?
5. Add logging at each step to identify where the pipeline breaks

**Acceptance criteria:**
1. Send a chat message, wait 5 seconds, query annotations table — annotations exist
2. Annotations have meaningful type/key/value (not empty or malformed)
3. Contradiction detection works when conflicting annotations exist
4. Pattern detection returns results when sufficient annotations accumulate

---

### Task 7.3: Fix NodeLabels to hover-only ✅

**What:** NodeLabels currently render always-on for every node. At 200+ nodes this is visual chaos. Switch to hover-only display.

**Changes:**
- `NodeLabels.tsx`: Only render label for hovered node (use raycaster hit from TraceCloud or a shared hover state)
- Alternative: render all labels but set visibility based on hover proximity

**Acceptance criteria:**
1. No labels visible by default
2. Hovering near a node shows its label
3. Label disappears when hover moves away
4. Performance maintained at 200+ nodes (no per-frame label recalculation for all nodes)

---

## Group B: Temporal Digest

### Task 7.4: Period summary generation (backend) ✅

**What:** Generate AI-synthesized narrative summaries for a time period. "Your thinking this month" — not a list of traces, but a narrative that identifies themes, tracks evolution, and notes contradictions. Summaries are stored as system traces in the graph (themselves retrievable in future context assembly).

**Depends on:** Sufficient trace data (~50+ traces across multiple domains). Can build and test with whatever data exists — doesn't need 200.

**Changes:**
- New: `services/temporal_digest.py` — `TemporalDigestService`
- Method `generate_period_summary(days: int = 30) -> Trace`:
  1. Fetch all traces in time window
  2. Cluster them (reuse hierarchical clustering)
  3. For each cluster: extract central traces, get annotations
  4. Detect cross-cluster contradictions/evolutions
  5. Send to LLM with structured prompt requesting narrative synthesis
  6. Store result as system trace (`source='system'`, content=narrative)
  7. Return the system trace
- Method `get_topic_evolution(query: str, days: int = 60) -> str`:
  1. Embed query, retrieve relevant traces across full time window
  2. Order chronologically
  3. Send to LLM: "How has this person's thinking about {topic} evolved?"
  4. Return narrative (not stored — on-demand)
- New route: `POST /api/digest` with `{ "days": 30 }` → triggers generation, returns narrative
- New route: `GET /api/digest/evolution?q={query}&days=60` → returns topic evolution narrative

**Acceptance criteria (→ tests in `test_phase7_digest.py`):**
1. Period summary generates coherent narrative (not a list) for time window
2. Narrative references specific traces by content (not IDs — human-readable)
3. Summary is stored as system trace with `source='system'`
4. System trace is embedded (retrievable in future context assembly)
5. Topic evolution returns chronological narrative for a given query
6. Empty time window returns graceful message, not error
7. LLM failure returns error message, doesn't crash
8. Summary trace has conversation_id = `'digest-{date}'` for grouping

---

### Task 7.5: "On This Day" resurfacing ✅

**What:** When a new session starts, check for relevant traces from 1 week / 1 month / 1 quarter ago. If found, include them as extra context in the first response's system prompt. Not as a notification — as natural context that makes the AI feel temporally aware.

**Depends on:** Traces with timestamps spanning weeks. Starts being useful ~1 week into daily use.

**Changes:**
- New: `services/resurfacing.py` — `ResurfacingService`
- Method `find_resurface_candidates(current_time: str) -> list[Trace]`:
  1. Check traces from exactly 7 ± 1 days ago
  2. Check traces from exactly 30 ± 2 days ago
  3. Check traces from exactly 90 ± 3 days ago
  4. Filter: only user traces with annotations (not empty chatter)
  5. Score by annotation richness (more annotations = more interesting to resurface)
  6. Return top 2-3 candidates
- `trace_context.py`: When building system prompt for first message of a new conversation, call `find_resurface_candidates()` and append to context
- Chat route detects "first message" by checking if conversation has zero existing traces

**Acceptance criteria (→ tests in `test_phase7_resurfacing.py`):**
1. Traces from ~7 days ago are found when they exist
2. Traces from ~30 days ago are found when they exist
3. Candidates are filtered to user traces only (not assistant responses)
4. Maximum 3 resurface candidates returned
5. Candidates appear in system prompt for first message of new conversation
6. Second message in same conversation does NOT include resurface context
7. No resurface candidates when no traces exist at those time offsets

---

### Task 7.6: Temporal digest in chat (frontend integration) ✅

**What:** User can ask "what have I been thinking about this month?" and get a rich narrative response with context markers pointing to anchor traces. Wire the `/api/digest/evolution` endpoint for topic-specific queries.

**This is NOT a separate UI.** It works through the existing chat.

**Depends on:** Task 7.4 (backend endpoints exist)

**Changes:**
- `chat.py`: Let standard retrieval + context assembly handle most "evolution" queries naturally. Only call `/api/digest` for explicit summary generation (triggered by explicit request like "summarize my last month" or "give me a digest").
- Response still streams, still stores as traces, still has context markers.

**Acceptance criteria:**
1. Asking about past thinking in chat produces responses referencing old traces
2. Context markers in response point to traces from the relevant time period
3. `/api/digest` endpoint callable from frontend (explicit chat command)
4. Digest response streams like normal chat response
5. Digest traces (stored as system traces) are retrievable in future conversations

---

## Group C: Demo Polish

### Task 7.7: Phase space visual tuning with real data ✅ (adaptive infra) / ⏳ (data-dependent verification)

**What:** With 100+ real traces loaded, tune visual parameters. Real multi-domain data should produce better separation than Mina's single-persona content.

**Depends on:** ~1 week of daily Voku use (50-100+ traces)

**Changes:** Frontend component tweaks only. No new files.

**Tuning targets:**
- TraceCloud: node size range at real scale
- EdgeMesh: opacity for k-NN edges at scale (1500+ edges may need lower opacity)
- ClusterCloud: shell radius calculation for real cluster spreads
- CameraController: default position for real trace spread
- Color gradient: verify warm→cool mapping across multi-week time span
- Retrieval glow: test that glow animation is visible among 100+ nodes

**Acceptance criteria:**
1. Phase space is visually readable with 100+ nodes (distinct clusters, not blob)
2. Clusters correspond to real thematic domains (career, academics, training, etc.)
3. Warm/cool color gradient spans the time range
4. Retrieval glow visible during chat
5. Default camera position shows full graph with readable structure
6. 60fps maintained

---

### Task 7.8: Demo deployment (Docker + Railway)

**What:** Containerize the application for demo deployment. Single Docker Compose with backend + frontend. Deploy to Railway (or Render as fallback).

**Depends on:** All other Phase 7 tasks complete, sufficient real data accumulated

**Changes:**
- New: `Dockerfile` (multi-stage: Python backend + Node frontend build)
- New: `docker-compose.yml`
- New: `.env.example` updated with all required vars
- Modified: Frontend API_BASE configurable via environment variable
- Modified: Backend CORS allows deployment domain

**Database strategy for demo:**
- Option A: Ship pre-seeded with Jaymin's real accumulated data (snapshot voku.db into image)
- Option B: Deploy empty + populate live during demo
- Decision deferred until data volume is known (~Mar 20)

**Acceptance criteria:**
1. `docker compose up` starts both backend and frontend
2. Frontend accessible at configured port
3. Chat works (Anthropic API key required — documented)
4. Phase space renders with accumulated data
5. No local filesystem dependencies (SQLite DB inside container)
6. Deployed URL loads within 5 seconds

---

### Task 7.9: Demo narrative script + walkthrough

**What:** Write the 60-second demo script and rehearse the walkthrough. Portfolio presentation — needs to be tight.

**Not code.** Output: `docs/DEMO_SCRIPT.md`

**Structure (from SPEC § Demo Narrative):**
1. Open — populated phase space, visible structure (real thinking, not synthetic)
2. Ask something spanning sessions — rich response with context markers
3. Summon phase space — clusters pulsing from retrieval
4. Zoom into a cluster — individual traces, connections, thread paths
5. Zoom out — clouds merge into orientations, topology visible
6. Temporal digest — "summarize my February" or "how has my thinking about Voku evolved?"
7. Close — the thesis in 2 sentences

**Acceptance criteria:**
1. Script times to ≤ 90 seconds when read aloud
2. Every feature demonstrated has working backend + frontend support
3. Demo queries pre-tested against real accumulated data
4. Fallback queries documented in case primary queries produce weak responses
5. Script includes setup instructions (start backend, frontend, ensure API key)

---

## Deferred (Post-Demo)

- **Time slider animation** — Watch topology evolve over time
- **Continuous zoom interpolation** — Smooth trace→cloud→orientation transitions
- **Thread path rendering** — Parent chain visualization on trace selection
- **Resource drop UI** — Drag file/URL into chat
- **Connection-type encoding in context markers** — Visual differentiation of semantic vs temporal vs intentional retrieval
- **Orientation-level terrain rendering** — Soft regions at max zoom-out

---

## Test Strategy

**New test files:**
- `test_phase7_digest.py` — Task 7.4 (period summary, topic evolution)
- `test_phase7_resurfacing.py` — Task 7.5 ("On This Day")

**Visual verification (no automated tests):**
- Task 7.7: Phase space visual tuning
- Task 7.8: Docker deployment
- Task 7.9: Demo script

**Real data as integration test:**
- 1-week gate: phase space shows ≥ 3 clusters from real multi-domain conversations
- 2-week gate: temporal digest produces meaningful narrative

---

## Traceability

| SPEC Requirement | Task | Test File |
|-----------------|------|-----------|
| "200+ traces with thematic structure" | 7.1 (daily use) | 1-week visual gate |
| "Annotation extraction functional" | 7.2 | manual + query check |
| "Period summary generation (narrative, not list)" | 7.4 | test_phase7_digest.py |
| "Period summaries stored as system traces" | 7.4 | test_phase7_digest.py |
| "'On This Day' resurfacing in first response" | 7.5 | test_phase7_resurfacing.py |
| "Demo mode deployment (Dockerfile + Railway)" | 7.8 | manual verification |
| "Context marker connection-type encoding" | DEFERRED | — |
| "Resource drop UI" | DEFERRED | — |

---

## Execution Order

| Window | Tasks | Gate |
|--------|-------|------|
| Mon Mar 2 | 7.1 ✅ + 7.2 ✅ + 7.3 ✅ + 7.4 ✅ + 7.5 ✅ | Group A + Group B complete. 271 tests. |
| Tue-Fri Mar 3-6 | Daily use accumulates data. 7.6 ✅ done Mon. | Group B gate: `pytest test_phase7_*` all green ✅ |
| Week of Mar 9-15 | 7.7 visual verification (when ~100 traces) + 7.8 (Docker prep) | Phase space shows distinct real clusters |
| Week of Mar 16-22 | 7.8 (deploy) + 7.9 (demo script) | Deployed URL works, script rehearsed |
| Mar 23-31 | Polish + rehearse | Demo-ready |

**Note:** Academics interrupt this schedule — CS5004 Lab03+Assignment03 (due Mar 8), CS5008 midterm (Mar 12), CS5004 Project Phase 1 (due Mar 15). Voku code tasks flex around academic deadlines. Daily Voku *use* continues regardless.

---

## Gates

| Group | Gate |
|-------|------|
| A (Data + Fixes) | Annotations extracting after chat. Phase space renders real data. Labels hover-only. |
| B (Digest) | `pytest test_phase7_digest.py test_phase7_resurfacing.py` all green. Chat about "my thinking" returns narrative with context markers. |
| C (Demo) | `docker compose up` → public URL → 90-second walkthrough completes without errors. |
