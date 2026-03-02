# CLAUDE.md

> Project context for AI-assisted development. Read this before making changes.

---

## Project

Voku is a transparent thinking environment where conversations become timestamped traces in a navigable knowledge graph — the personal context layer any AI agent can query.

**Status:** v2 architecture, Phases 0-6 complete, Phase 7 in progress. See `docs/STATE.md` for current position.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLite (single file, WAL mode) |
| Embeddings | bge-base-en-v1.5 via sentence-transformers, numpy vector search |
| LLM (chat) | Anthropic Claude (streaming via SDK) |
| LLM (extraction) | Groq (cloud) / Ollama (local) via abstract provider interface |
| Frontend | React 19, TypeScript, Vite 7, Tailwind v4 |
| Visualization | Three.js 0.183 via react-three-fiber 9, InstancedMesh rendering |

Local-first. No Docker, no cloud database. API keys required for Anthropic (chat) and Groq (annotation extraction).

---

## Quick Start

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload                # localhost:8000
# Schema auto-creates on first run. No manual migration needed.

# Frontend
cd frontend
NODE_ENV=development npm install             # see Known Issues
npm run dev                                  # localhost:5173

# Tests
cd backend && source venv/bin/activate
pytest                                       # 241 tests
pytest tests/test_phase5_*.py -v             # Phase 5 tests only
```

### Known Issues

- `NODE_ENV=production` in `~/.zshrc` causes `npm install` to skip devDependencies. Prefix with `NODE_ENV=development`.
- Phase space needs ~50+ traces for meaningful visual structure. Fewer than 5 traces get random jittered positions (no UMAP).

---

## Architecture

### Data Model (v2 — Five Tables)

```
traces          id, timestamp, content, conversation_id, parent_trace_id, source
annotations     id, trace_id, type, key, value, confidence, extracted_at, extractor
connections     source_id, target_id, type, weight, created_at
resources       id, trace_id, type, uri, relationship, summary
embeddings      trace_id, model, vector, computed_at
```

Traces are immutable ground truth. Annotations are computed, re-extractable, category-free. Full schema in `migrations/v2_schema.sql`, design rationale in `docs/SPEC.md`.

### Service Layer

```
services/
├── storage/                  SQLite + vector search (ABC + implementation)
│   ├── __init__.py           TraceStorageService ABC
│   ├── sqlite_trace.py       SQLiteTraceStorage (traces, annotations, connections, embeddings)
│   └── models.py             Trace, Annotation, Connection, SimilarTrace dataclasses
├── embedding/bge.py          bge-base-en-v1.5 embedder
├── providers/                LLM abstraction (Groq, Ollama)
├── trace_retrieval.py        Vector search + recency weighting + graph expansion + intention boost
├── trace_context.py          System prompt assembly from retrieved traces + contradiction cues
├── annotation.py             LLM-based annotation extraction (async)
├── background.py             Background task: annotations + temporal connections after chat
├── connections.py            Temporal + semantic connection computation
├── contradiction.py          Detect opposing annotations on same key
├── cluster_metadata.py       LLM labels for clusters (+ keyword fallback)
├── patterns.py               Frequency pattern detection with provisional language
├── trace_projection.py       UMAP + hierarchical DBSCAN + k-NN edges
└── router.py                 Provider routing (Groq/Ollama)
```

### Routes

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat` | POST | Streaming chat with trace-based context. Background annotation extraction. |
| `/api/phase-space` | GET | Multi-resolution data: traces + clusters + orientations + edges |
| `/api/patterns` | GET | Recurring annotation patterns within timeframe |
| `/api/traces/{id}` | GET | Single trace with annotations and connections |
| `/api/traces/connections/compute` | POST | Recompute all connections (batch) |
| `/api/history` | GET | All conversations with traces |
| `/api/conversations` | POST | Create new conversation |
| `/api/status` | GET | Health check |

### Frontend

```
src/
├── pages/Workspace.tsx           Main layout: chat + summonable phase space
├── hooks/usePhaseSpace.ts        Lazy data hook for /api/phase-space
├── types/phase-space.ts          TypeScript interfaces matching backend
├── components/
│   ├── chat/                     ChatPanel, ChatMessages, ChatInput, ChatHeader
│   │   ├── ContextMarker.tsx     Interactive [N] citations with hover tooltips
│   │   └── Markdown.tsx          Lightweight renderer with citation parsing
│   └── phase-space/              Summonable 3D visualization
│       ├── PhaseSpaceContainer   Slide-in overlay (⌘+Space toggle)
│       ├── PhaseSpaceScene       R3F Canvas + lighting + composition
│       ├── TraceCloud            InstancedMesh nodes (recency color, retrieval glow)
│       ├── NodeLabels            Hover-only labels (drei Html, billboard)
│       ├── EdgeMesh              k-NN edges (LineSegments, single draw call)
│       ├── ClusterCloud          Translucent cluster shells
│       └── CameraController      OrbitControls + focus animation
└── styles/tokens.css             Design tokens (colors, typography, spacing)
```

---

## Code Conventions

### Python (Backend)

- **Type hints everywhere.** Function signatures, return types, variable annotations.
- **Dataclasses** for domain models. Pydantic `BaseModel` for API schemas.
- **Docstrings** on classes and public methods. One-line summary + optional detail.
- **Import order:** stdlib → third-party → app modules.
- **SQL:** Raw SQLite via `sqlite3`, `Row` factory, WAL mode + foreign keys.
- **Vectors:** numpy for all embedding operations. `float32` dtype.
- **New services** follow the pattern: ABC in `__init__.py`, implementation in named file, models in `models.py`.
- **Tests:** pytest, mirror source structure, real fixtures in `tests/fixtures/real/`.

### TypeScript (Frontend)

- **Functional components** with hooks. No class components.
- **Tailwind v4** for styling. Design tokens in `src/styles/tokens.css`.
- **Three.js** via react-three-fiber declarative API. InstancedMesh for batch rendering.

---

## Design Constraints (Summary)

Full hierarchy in `docs/CONSTRAINTS.md`. Key rules:

1. **Conversation quality must improve with accumulated context** (Tier 0).
2. **Anti-collapse principle:** features must preserve the cloud, not collapse to point estimates (Tier 0).
3. **No predefined categories.** Annotation types emerge from extraction (Tier 2).
4. **Tests define done.** No component ships without tests (Tier 2).
5. **Single-file SQLite.** Recursive CTEs handle all traversal (Tier 3).

---

## Documentation

| Document | Purpose | Read when |
|----------|---------|-----------|
| `docs/STATE.md` | Current build position, next steps | Every session start |
| `docs/SPEC.md` | v2 product definition, data model, UI, build plan | Entering a build phase |
| `docs/TASKS_PHASE7.md` | Phase 7 tasks (real-data strategy, temporal digest, demo) | Current phase |
| `docs/CONSTRAINTS.md` | Decision hierarchy for tradeoffs | Making design decisions |
| `docs/archive/TASKS_PHASE5.md` | Phase 5 task breakdown (complete) | Reference only |
| `docs/archive/TASKS_PHASE6.md` | Phase 6 task breakdown (complete) | Reference only |
