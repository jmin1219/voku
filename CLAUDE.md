# CLAUDE.md

> Project context for AI-assisted development. Read this before making changes.

---

## Project

Voku is a transparent thinking environment where conversations become timestamped traces in a navigable knowledge graph — the personal context layer any AI agent can query.

**Status:** v2 architecture. Spec complete. See `docs/STATE.md` for current build phase and next steps.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLite (single file, WAL mode) |
| Embeddings | bge-base-en-v1.5 via sentence-transformers, numpy vector search |
| LLM | Groq (cloud) / Ollama (local) via abstract provider interface |
| Frontend | React 19, TypeScript, Vite 7, Tailwind v4 |
| Visualization | Three.js 0.183 via react-three-fiber 9, InstancedMesh rendering |
| UI Components | shadcn/ui (Radix primitives) |

Local-first. No Docker, no cloud database. Groq API key required only for LLM calls.

---

## Quick Start

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload                # localhost:8000

# Frontend
cd frontend
NODE_ENV=development npm install             # see Known Issues
npm run dev                                  # localhost:5173

# Tests
cd backend && source venv/bin/activate
pytest                                       # all tests
pytest tests/test_storage.py -v              # single file
pytest -k "test_trace"                       # by pattern
```

### Known Issues

- `NODE_ENV=production` in `~/.zshrc` causes `npm install` to skip devDependencies. Prefix with `NODE_ENV=development`.
- Stale remote branches: `origin/feat/conversation-extraction`, `origin/feat/extraction-v2`.

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

Traces are immutable ground truth. Annotations are computed, re-extractable, category-free — no predefined types at the schema level. Full schema in `docs/SPEC.md`.

### Service Layer Pattern

Services use abstract base classes with concrete implementations:

```
services/storage/__init__.py     → StorageService (ABC)
services/storage/sqlite_storage.py → SQLiteStorage(StorageService)
services/storage/models.py       → dataclass models (StoredProposition, SimilarResult)
```

Shared singletons live in `app/dependencies.py` — storage, embedder, retrieval, and context assembly are instantiated once and injected via FastAPI dependency injection. This ensures the in-memory embedding cache stays consistent across routes.

### Request/Response Pattern

Routes use Pydantic models for request validation. Streaming responses use FastAPI's `StreamingResponse` with SSE (Server-Sent Events) for real-time chat.

---

## Code Conventions

### Python (Backend)

- **Type hints everywhere.** Function signatures, return types, variable annotations.
- **Dataclasses** for domain models (`@dataclass`). Pydantic `BaseModel` for API schemas.
- **Docstrings** on classes and public methods. Format: one-line summary, optional detail paragraph.
- **Import order:** stdlib → third-party → app modules. Relative imports within packages (`from . import`), absolute for cross-package (`from app.services.storage import`).
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- **SQL:** Raw SQLite via `sqlite3` module, `Row` factory for dict-like access. WAL mode + foreign keys enabled in every connection.
- **Vectors:** numpy for all embedding operations. `float32` dtype. Cosine similarity computed manually (normalize + dot product).
- **New services** follow the pattern: ABC in `__init__.py`, implementation in named file, models in `models.py`.

### TypeScript (Frontend)

- **Functional components** with hooks. No class components.
- **Tailwind v4** for styling. Design tokens in `src/styles/`.
- **Three.js** via react-three-fiber declarative API. InstancedMesh for batch rendering.
- **shadcn/ui** for standard UI components (dialogs, buttons, labels).

### Testing

- pytest with `conftest.py` for path setup.
- Test files mirror source: `test_storage.py` tests `storage/`, `test_retrieval.py` tests `retrieval.py`.
- Real conversation fixtures in `tests/fixtures/real/` (21 conversations).
- Golden evaluation queries in `tests/golden/`.

---

## Directory Structure

```
voku/
├── CLAUDE.md              ← this file
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI entry, CORS, lifespan
│   │   ├── config.py          Environment settings (Pydantic)
│   │   ├── dependencies.py    Shared service singletons
│   │   ├── routes/            API endpoints (chat, extract, propositions)
│   │   ├── models/            Shared data models
│   │   ├── services/
│   │   │   ├── storage/       SQLite + vector search
│   │   │   ├── embedding/     bge-base-en-v1.5
│   │   │   ├── extraction/    LLM proposition extraction (v1)
│   │   │   ├── providers/     Groq / Ollama abstraction
│   │   │   ├── conversation/  Chat session management
│   │   │   ├── user_model/    Dimension assignment + context (v1)
│   │   │   ├── retrieval.py   Temporal-weighted vector search
│   │   │   └── projection.py  UMAP + DBSCAN clustering
│   │   └── mcp/               MCP server skeleton
│   ├── tests/
│   ├── scripts/               Batch processing, data migration
│   ├── data/                  SQLite databases
│   └── migrations/            Schema SQL files
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── chat/          ChatHeader, ChatInput, ChatMessages
│       │   ├── phase-space/   NodeCloud, EdgeMesh, Scene, CameraController
│       │   └── ui/            shadcn/ui components
│       ├── pages/             Workspace layout
│       ├── styles/            Design tokens, typography
│       └── types/             TypeScript type definitions
└── docs/
    ├── STATE.md               Current position + session log
    ├── SPEC.md                v2 product definition + build sequence
    ├── CARRY_FORWARD.md       v1 → v2 migration file map
    ├── CONSTRAINTS.md         Decision hierarchy (Tier 0–3)
    └── archive/v1/            Archived v1 documentation
```

---

## Design Constraints (Summary)

Full hierarchy in `docs/CONSTRAINTS.md`. Key rules:

1. **Conversation quality must improve with accumulated context** (Tier 0). If it doesn't, nothing else matters.
2. **No predefined categories.** Annotation types emerge from extraction, not schema design (Tier 2).
3. **Vertical slices first.** End-to-end through all layers before broadening (Tier 2).
4. **Tests define done.** No component ships without tests (Tier 2).
5. **Single-file SQLite.** No graph databases. Recursive CTEs handle all traversal patterns at scale (Tier 3).
6. **Interfaces over implementations.** Every service has an ABC. Swapping providers is a config change (Tier 3).

---

## Documentation

| Document | Purpose | Read when |
|----------|---------|-----------|
| `docs/STATE.md` | Current build position, decisions, next steps | Every session start |
| `docs/SPEC.md` | v2 product definition, data model, UI architecture, build plan | Entering a build phase |
| `docs/CARRY_FORWARD.md` | Exact file map: keep / refactor / rebuild / drop | During migration |
| `docs/CONSTRAINTS.md` | When two design goals conflict, the higher tier wins | Making tradeoff decisions |
