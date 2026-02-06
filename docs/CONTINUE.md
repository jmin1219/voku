# Voku Continuation Prompt

> Use this to resume work in a new chat session.

---

## Context

**Project:** Voku v0.3 — Knowledge-first cognitive prosthetic
**Phase:** Vertical slice (text → extraction → graph → visualization)
**Last Session:** Feb 06, 2026
**Repo state:** Clean — v0.2 stripped, Kuzu 0.11.3, 18 tests passing

## What's Done

- Phase A complete: Kuzu schema, node/edge CRUD, constraint validation
- LLM providers: Groq `complete()` + Ollama abstraction
- Frontend shell: React + Tailwind + shadcn/ui (no graph UI yet)
- Full project review + top-down analysis completed

## What's Next: Vertical Slice

Build one thin path through all layers:

1. **API endpoint** — `POST /api/chat` accepting user text
2. **LLM extraction** — Send text to Groq, get structured propositions back as JSON
3. **Graph write** — Create LeafNodes + edges from extracted propositions
4. **Embedding** — Generate with bge-base-en-v1.5, store in Kuzu (v0.11.3 has HNSW)
5. **Frontend** — React Flow graph view rendering nodes from backend

### Learning priorities (do hands-on, not abstract)
- Load sentence-transformers, embed a sentence, compute cosine similarity
- Send extraction prompt to Groq `complete()`, handle malformed JSON
- React Flow basics: render hardcoded graph, then wire to backend

### What Claude handles vs what Jaymin must understand
- **Claude:** Boilerplate wiring, React Flow setup, WebSocket scaffolding, CSS
- **Jaymin:** What embeddings represent, what LLM extraction produces, why graph structure enables the queries in DESIGN_V03.md

## Key Files

```
backend/app/services/graph/      # Kuzu schema + CRUD (working)
backend/app/services/providers/  # Groq + Ollama (working)
backend/app/main.py              # FastAPI entry (health check only)
backend/tests/test_graph.py      # 18 passing, 5 skipped
docs/DESIGN_V03.md               # Architecture spec (842 lines)
docs/STATE.md                    # Status tracker
```

## Run Tests

```bash
cd /Users/jayminchang/Documents/projects/voku/backend
source venv/bin/activate
python -m pytest tests/test_graph.py -v
```

## Resume Command

"Continue Voku vertical slice — start with the LLM extraction step: send a test conversation turn to Groq and see what structured output comes back."
