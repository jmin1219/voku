# CLAUDE.md

> Project context for AI-assisted development. Read this before making changes.

---

## Project

Voku is a transparent thinking environment where conversations become timestamped traces in a navigable knowledge graph — the personal context layer any AI agent can query.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, SQLite (single file, WAL mode) |
| Embeddings | bge-base-en-v1.5 via sentence-transformers, numpy vector search |
| LLM (chat) | Anthropic Claude (streaming via SDK) |
| LLM (extraction) | Groq (cloud) / Ollama (local) via abstract provider interface |
| Frontend | React 19, TypeScript, Vite 7, Tailwind v4 |
| Visualization | Three.js 0.183 via react-three-fiber 9, InstancedMesh rendering |
| Deployment | Docker (multi-stage), Railway |

Local-first. API keys required for Anthropic (chat) and Groq (annotation extraction).

---

## Quick Start

```bash
# Docker (recommended)
docker compose up --build              # localhost:8000

# Local development
cd backend && source venv/bin/activate
uvicorn app.main:app --reload          # localhost:8000

cd frontend
NODE_ENV=development npm install
npm run dev                            # localhost:5173

# Tests
cd backend && source venv/bin/activate
pytest                                 # 271 tests
```

### Known Issues
- `NODE_ENV=production` in `~/.zshrc` causes `npm install` to skip devDependencies. Prefix with `NODE_ENV=development`.
- Phase space needs ~50+ traces for meaningful visual structure.

---

## Architecture

### Data Model (Five Tables)

```
traces          id, timestamp, content, conversation_id, parent_trace_id, source
annotations     id, trace_id, type, key, value, confidence, extracted_at, extractor
connections     source_id, target_id, type, weight, created_at
resources       id, trace_id, type, uri, relationship, summary
embeddings      trace_id, model, vector, computed_at
```

Traces are immutable. Annotations are computed, re-extractable, category-free.
Full schema in `migrations/v2_schema.sql`, design rationale in `docs/SPEC.md`.

### Service Layer

```
services/
├── storage/              SQLite + in-memory vector search
│   ├── sqlite_trace.py   Traces, annotations, connections, embeddings
│   └── models.py         Trace, Annotation, Connection dataclasses
├── embedding/bge.py      bge-base-en-v1.5 embedder
├── providers/            LLM abstraction (Groq, Ollama)
├── trace_retrieval.py    Vector search + recency weighting + graph expansion
├── trace_context.py      System prompt assembly from retrieved traces
├── annotation.py         Async LLM-based annotation extraction
├── background.py         Post-chat annotation + connection computation
├── connections.py        Temporal + semantic connection computation
├── contradiction.py      Detect opposing annotations on same key
├── temporal_digest.py    Period summaries + topic evolution
├── resurfacing.py        "On This Day" trace resurfacing
├── trace_projection.py   UMAP + DBSCAN clustering + k-NN edges
└── router.py             Provider routing (Groq/Ollama)
```

### Routes

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat` | POST | Streaming chat with trace-based context |
| `/api/phase-space` | GET | Traces + clusters + orientations + edges |
| `/api/digest` | POST | Generate period summary narrative |
| `/api/digest/evolution` | GET | Topic evolution over time |
| `/api/traces/{id}` | GET | Single trace with annotations |
| `/api/history` | GET | All conversations with traces |
| `/api/status` | GET | Health check |

---

## Code Conventions

- **Python:** Type hints everywhere. Dataclasses for models, Pydantic for API schemas. Raw SQLite with Row factory.
- **TypeScript:** Functional components with hooks. Tailwind v4 for styling. Three.js via react-three-fiber.
- **Tests:** pytest, 271 passing. Mirror source structure.

---

## Design Constraints

See `docs/CONSTRAINTS.md`. Key rules:
1. Conversation quality must improve with accumulated context.
2. No predefined categories — annotation types emerge from extraction.
3. Immutable traces, improvable annotations.
4. Single-file SQLite. Local-first.
5. Tests define done.
