# Voku

> A personal temporal knowledge graph that extracts beliefs from conversation, organizes them into a graph, and shows how your thinking evolves.

## What Voku Is

You talk to Voku naturally. It extracts atomic propositions from your speech, embeds them semantically, deduplicates against your existing knowledge, and writes unique beliefs into a graph — building a structured model of how you think.

**Core insight:** Productivity planners take goals as input. Voku questions whether stated goals are *real* — or performance, or inherited, or outdated. Self-understanding is the anchor; goals emerge from seeing yourself clearly.

**What it surfaces:**
- Discrepancies between stated intentions and observed patterns
- How your beliefs evolve over time (contradiction detection, refinement tracking)
- Connections in your thinking you haven't noticed

## Architecture

| Layer | Implementation | Status |
|-------|---------------|--------|
| **Extraction** | LLM-based proposition extraction (Groq/Ollama) with 5-layer validation, voice preservation | ✅ Working |
| **Embedding** | bge-base-en-v1.5, 768-dim vectors, cosine similarity search | ✅ Working |
| **Deduplication** | Semantic similarity threshold (>0.95 = duplicate, 0.85-0.95 = related) | 🔧 Wiring |
| **Graph Storage** | Kuzu 0.11.3 — 4 node types, 6 edge types, 18 tests passing | ✅ Working |
| **Frontend** | React + TypeScript + Tailwind (placeholder) | ⏳ Planned |
| **Visualization** | React Flow graph rendering | ⏳ Planned |

```
User speaks → ExtractionService → EmbeddingService → Dedup → GraphOperations → Kuzu
                  (Groq LLM)      (bge-base-en-v1.5)         (LeafNode + NodeEmbedding)
```

## Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Dual Space** | User sees confirmed graph; Voku reasons in hidden Organization Space before proposing |
| **Bi-Temporal Model** | `valid_from`/`valid_to` (when you believed it) vs `recorded_at` (when Voku learned it) |
| **Ghost Persistence** | Never delete — graduated visibility preserves history |
| **Goal-Anchored Fields** | `node_purpose`, `source_type`, `signal_valence` enable intention vs. pattern queries |
| **Extraction ≠ Abstraction** | Extraction produces LeafNodes (atomic). Named abstractions (InternalNodes) emerge from clustering — separate operation |

## Tech Stack

| Component | Choice | Version |
|-----------|--------|---------|
| Graph Database | Kuzu | 0.11.3 (archived Oct 2025, feature-complete for requirements) |
| Backend | FastAPI | 0.128.0 |
| Frontend | React + React Flow | TBD |
| LLM (default) | Groq | llama-3.3-70b-versatile |
| LLM (private) | Ollama | Local |
| Embeddings | bge-base-en-v1.5 | via sentence-transformers 3.4.1 |

## Current Status

**v0.3: Knowledge-First Graph — Phase 1 in progress**

| Phase | Status |
|-------|--------|
| A: Kuzu Foundation | ✅ Complete — schema, CRUD, edges, 18 tests |
| 0: LLM Extraction | ✅ Complete — proposition extraction, voice preservation |
| 1: Extraction → Graph Pipeline | 🎯 Steps 6/10 — extraction, embedding, dedup wiring next |
| 2: Batch Processing + Clustering | Planned — emergent pattern detection |
| 3: Graph Visualization | Planned — React Flow |

**Approach:** Vertical slice (text → extraction → embedding → dedup → graph → visualization) rather than completing phases sequentially. See [docs/STATE.md](./docs/STATE.md) for implementation details.

## Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add GROQ_API_KEY
python -m pytest tests/test_graph.py -v  # 18 passed
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/DESIGN_V03.md](./docs/DESIGN_V03.md) | Complete architecture specification |
| [docs/ARCHITECTURE_DIAGRAMS.md](./docs/ARCHITECTURE_DIAGRAMS.md) | Mermaid diagrams (schema, data flow, system architecture) |
| [docs/ADR_001_BATCHING_STRATEGY.md](./docs/ADR_001_BATCHING_STRATEGY.md) | Why per-turn now, batch processing later |
| [docs/STATE.md](./docs/STATE.md) | Implementation status, session log, decisions made |

## License

MIT

---

**Built by:** Jaymin Chang
**Portfolio:** [github.com/jmin1219](https://github.com/jmin1219) | [@ChangJaymin](https://twitter.com/ChangJaymin)
