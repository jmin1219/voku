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
              ┌─────────────────────┴─────────────────────┐
              │                                           │
         Kuzu (Graph)                              SQLite (Auxiliary)
         User + Organization Space                 Conversations, Traces
         Multi-aspect Embeddings                   Full-text Search
```

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Graph Database | Kuzu | Native Cypher, community detection, embedded |
| Auxiliary Storage | SQLite + FTS5 | Conversations, traces, settings |
| Frontend | React + React Flow | Graph visualization |
| LLM (default) | Groq | Fast, free tier |
| LLM (private) | Ollama | Local, no data leaves machine |
| Embeddings | bge-base-en-v1.5 | 768 dim, strong retrieval benchmarks |

## Current Status

**v0.3: Knowledge-First Graph** — Implementation in progress

| Phase | Hours | Status |
|-------|-------|--------|
| A: Kuzu Foundation | 4-5 | 🔵 Starting |
| B: Auxiliary Storage | 2-3 | Planned |
| C: Processing Pipeline | 5-6 | Planned |
| D: Multi-Aspect Embeddings | 2-3 | Planned |
| E: Document Import | 2-3 | Planned |
| F: Chat + Graph UI | 4-5 | Planned |

**Target:** Demo-ready April 2026

## Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add GROQ_API_KEY
uvicorn app.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm run dev
```

## Documentation

- **[docs/DESIGN_V03.md](./docs/DESIGN_V03.md)** — Complete architecture specification
- **[docs/STATE.md](./docs/STATE.md)** — Implementation status, decisions made
- **[docs/ARCHITECTURE_DIAGRAMS.md](./docs/ARCHITECTURE_DIAGRAMS.md)** — Visual system diagrams

## Interview Talking Points

**"Why Kuzu over SQLite for graph?"**  
Graph traversal is central — finding paths, detecting communities, measuring centrality. SQLite recursive CTEs work but don't express graph semantics. Kuzu gives native Cypher and built-in algorithms.

**"How does multi-aspect embedding work?"**  
Four embeddings per node: content, title, context (with parents), and hypothetical queries. Query embedding enables "What guides my decisions?" to match decision principles even without literal keyword overlap.

**"What's the organization layer?"**  
Voku's working memory — pattern detection, hypothesis formation — that shouldn't clutter user's graph. Inspectable: users can ask "why did you suggest this?" and see reasoning.

**"What makes this personal, not just a knowledge base?"**  
node_purpose (observation/pattern/belief/intention/decision) + source_type (explicit/inferred) + signal_valence (positive/negative/neutral) enable the core query: "Where does my behavior contradict my stated intentions?"

## License

MIT

---

**Built by:** Jaymin Chang  
**Portfolio:** [github.com/jmin1219](https://github.com/jmin1219) | [@ChangJaymin](https://twitter.com/ChangJaymin)  
**Repo:** https://github.com/jmin1219/voku
