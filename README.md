# Voku

> A knowledge-first cognitive prosthetic that extracts beliefs from conversation, organizes them into a graph, and shows how your thinking evolves.

## What Voku Is

You talk to Voku naturally. It extracts your beliefs into a graph — watch it build as you speak.

**Core insight:** Productivity planners take goals as input. Voku questions whether stated goals are *real* — or performance, or inherited, or outdated. Self-understanding is the anchor; goals emerge from seeing yourself clearly.

**What it surfaces:**
- Discrepancies between stated intentions and observed patterns
- How your beliefs evolve over time (contradiction detection, refinement tracking)
- Gaps in your thinking ("You've discussed X and Y but never Z")

## Key Innovations

| Innovation | Description |
|------------|-------------|
| **Research Depth (0-10)** | Not a toggle — every operation behaves differently based on depth |
| **Dual Space Architecture** | User sees confirmed graph; Voku reasons in hidden workspace before proposing |
| **Bi-Temporal Model** | When you believed something vs. when Voku learned it |
| **Multi-Aspect Embeddings** | 4 embeddings per node enable semantic retrieval beyond literal matching |
| **Ghost Persistence** | Never delete — graduated visibility preserves history |
| **Goal-Anchored Fields** | node_purpose, source_type, signal_valence enable intention vs. pattern comparison |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  CHAT (1/3)              │  GRAPH VIEW (2/3)                        │
│  Conversation + Depth    │  React Flow + Ghost Nodes + Evolution    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                           FastAPI Backend
                    Processing Pipeline (5 stages)
                                    │
                            Kuzu (Graph DB)
                  User + Organization Space
                  Multi-aspect Embeddings + HNSW Vector Search
```

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Graph Database | Kuzu 0.11.3 | Native Cypher, HNSW vector search, graph algorithms, embedded |
| Backend | FastAPI | Async, auto-docs, WebSocket support |
| Frontend | React + React Flow | Graph visualization |
| LLM (default) | Groq | Fast, free tier |
| LLM (private) | Ollama | Local, no data leaves machine |
| Embeddings | bge-base-en-v1.5 | 768 dim, strong retrieval benchmarks |

## Current Status

**v0.3: Knowledge-First Graph**

| Phase | Status |
|-------|--------|
| A: Kuzu Foundation | ✅ Complete — schema, CRUD, 18 tests |
| C: Processing Pipeline | 🎯 Next — vertical slice approach |
| D: Embeddings | Planned |
| F: Chat + Graph UI | Planned |

**Approach:** Building a vertical slice (text → extraction → graph → visualization) rather than completing phases sequentially. See [docs/STATE.md](./docs/STATE.md) for details.

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

- **[docs/DESIGN_V03.md](./docs/DESIGN_V03.md)** — Complete architecture specification
- **[docs/ARCHITECTURE_DIAGRAMS.md](./docs/ARCHITECTURE_DIAGRAMS.md)** — Visual system diagrams
- **[docs/STATE.md](./docs/STATE.md)** — Implementation status, decisions made
- **[docs/CONTINUE.md](./docs/CONTINUE.md)** — Session continuation prompt

## License

MIT

---

**Built by:** Jaymin Chang
**Portfolio:** [github.com/jmin1219](https://github.com/jmin1219) | [@ChangJaymin](https://twitter.com/ChangJaymin)
