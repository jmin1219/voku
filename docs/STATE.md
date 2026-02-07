# Voku State

> Current position, decisions made, blockers. Updated each session.

**Last Updated:** 2026-02-06 (Post-cleanup)

---

## Current Phase

**v0.3: Knowledge-First Graph**

| Phase | Est. Hours | Status |
|-------|-----------|--------|
| A: Kuzu Foundation | 4.5 | ✅ Complete (Feb 02) |
| B: Auxiliary Storage | 2-3 | ⏭️ Skipped for now |
| C: Processing Pipeline | 5-6 | 🎯 Next (vertical slice) |
| D: Multi-Aspect Embeddings | 2-3 | Planned |
| E: Document Import | 2-3 | Deferred |
| F: Chat + Graph UI | 4-5 | Planned |

**Strategy shift (Feb 06):** Build a vertical slice through C→D→F rather than completing phases sequentially. One thin path: user types text → LLM extracts → nodes created → embeddings stored → graph renders.

Phase B (SQLite auxiliary storage) deferred — conversations can live in memory for demo. Phase E (document import) deferred — not needed for portfolio demo.

---

## What Exists

### Backend
- **Graph layer** (`services/graph/`): Kuzu schema, constants, CRUD operations — 18 tests passing
- **LLM providers** (`services/providers/`): Groq + Ollama abstraction with `complete()` method
- **FastAPI app**: Health check only — no graph routes yet

### Frontend  
- React + TypeScript + Tailwind + shadcn/ui primitives
- Single route placeholder (Home.tsx)
- No graph visualization yet

### Tests
- 18 passing, 5 skipped (embeddings + graph integrity — future work)
- TDD workflow: `cd backend && source venv/bin/activate && python -m pytest tests/test_graph.py -v`

---

## Technology Stack

| Component | Choice | Version |
|-----------|--------|---------|
| Graph Database | Kuzu | 0.11.3 (final release, archived Oct 2025) |
| Embeddings | bge-base-en-v1.5 | via sentence-transformers 3.4.1 |
| Backend | FastAPI | 0.128.0 |
| Frontend | React + React Flow | TBD |
| LLM (default) | Groq | llama-3.3-70b-versatile |
| LLM (private) | Ollama | local |

**Kuzu note:** Project archived Oct 2025. v0.11.3 is feature-complete for Voku (Cypher, HNSW vector search, graph algorithms). Community forks exist (Bighorn, LadybugDB, RyuGraph) but are early. Pragmatic choice for portfolio timeline.

---

## v0.3 Architecture Summary

**Vision:** Self-understanding as anchor, goals as emergent byproduct. Surfaces discrepancies between stated intentions and observed patterns.

**Core concepts:**
- Research Depth (0-10) as architectural axis
- User Space (visible graph) + Organization Space (Voku's hidden workspace)
- Bi-temporal model: valid_from/valid_to (belief time) + recorded_at (system time)
- Ghost persistence: never delete, graduated visibility
- node_purpose / source_type / signal_valence enable intention-vs-pattern queries

See `docs/DESIGN_V03.md` for complete specification.

---

## Design Rationale: Feature ↔ Failure Mode Mapping

Every core feature traces to a documented failure mode from 60+ Claude Desktop conversations (Dec 2025 — Feb 2026).

| Feature | Claude Desktop Failure It Solves | Evidence |
|---------|----------------------------------|----------|
| **Persistent graph** | Context amnesia across sessions — each new chat starts from zero | Memory edits compress and mutate details (e.g., $96K→$9K hallucination, Jan 7) |
| **Bi-temporal model** | Compression mutation — summaries overwrite source data | Immutable `recorded_at` prevents signal loss; `valid_from/valid_to` tracks belief evolution |
| **Ghost persistence** | Aggressive compression loses signal | "Claude leaves me with a 1-2 paragraph summary of a 20-minute lecture" |
| **Semantic dedup** | Duplicate note creation without checking existing concepts | INIT phase exists specifically because Claude creates duplicates without listing first |
| **Dual space (user/org)** | Manual fragile organization — 3 vault restructures in 6 weeks | Organization space proposes structure; user confirms. Automates what naming conventions workaround |
| **Graph traversal** | Flat keyword retrieval can't find reasoning chains | `conversation_search` finds keyword matches, not paths through thinking |
| **Extraction → structured data** | Paraphrasing mutates intent | Propositions stored as structured nodes, not Claude summaries |

**Deferred until post-demo validation:**

| Feature | Status | Reasoning |
|---------|--------|-----------|
| **Research Depth 0-10** | Defer | No documented friction maps to "I wish processing were lighter/deeper." Friction is organization + temporal, not depth. Build if usage reveals need. |
| **Multi-aspect embeddings (4/node)** | Defer — start with single embedding | Retrieval problems are about Claude not reading right files and creating duplicates, not semantic similarity returning wrong results. Single bge-base-en-v1.5 likely sufficient. Add aspects where single embedding measurably fails. |

**Key risk for vertical slice:** Automated extraction may produce technically correct but emotionally flat propositions. The reason "the internal monitor" works is collaborative naming through dialogue. Test whether extracted propositions feel like *your* concepts or clinical summaries. If flat, add interactive refinement step (already in design: "AI proposes, human confirms").

---

## Session Log

| Date | Hours | Completed |
|------|-------|-----------|
| Jan 30 | — | Architecture finalized, STATE.md synced |
| Jan 31 | 1.5 | Phase A: Kuzu schema complete (schema.py) |
| Feb 01 | 1.5 | Phase A: Node CRUD operations, 6 tests |
| Feb 01 | 1.0 | Phase A: Edge operations, constants.py, 13 tests |
| Feb 02 | 0.5 | Phase A: Complete — internal nodes, get_related(), 18 tests |
| Feb 06 | — | Full project review, strip v0.2, upgrade Kuzu 0.8→0.11.3, clean docs |
| Feb 06 | — | 60+ conversation retrospective: mapped every feature to documented failure mode. Deferred Research Depth + Multi-Aspect Embeddings to post-demo. |

---

## Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| **Strip v0.2 (BillyAI)** | Fitness/finance features muddy Voku's identity; clean repo tells one story | Feb 06 |
| **Defer Research Depth 0-10** | No documented friction maps to variable processing depth; friction is organization + temporal | Feb 06 |
| **Defer Multi-Aspect Embeddings** | Start with single embedding; retrieval problems are organizational not semantic | Feb 06 |
| **Feature↔Failure mapping** | Every core feature must trace to a documented Claude Desktop failure mode | Feb 06 |
| **Upgrade Kuzu 0.8→0.11.3** | Gets native HNSW vector search, graph algorithms, pre-bundled extensions | Feb 06 |
| **Vertical slice strategy** | Build one thin path through all layers vs completing phases sequentially | Feb 06 |
| **Skip Phase B for now** | SQLite auxiliary storage is infrastructure, not demo material | Feb 06 |
| **Portfolio framing** | Voku is a research prototype with product potential, not a product | Feb 06 |
| **Kuzu despite archiving** | v0.11.3 covers all requirements; defensible interview talking point | Feb 06 |
| **Renamed to Voku** | Professional branding; voku.app domain available | Jan 31 |
| **Goal-anchored philosophy** | Self-understanding as anchor; goals emerge from seeing yourself clearly | Jan 31 |
| **Kuzu over SQLite** | Native Cypher, community detection, path algorithms | Jan 30 |
| **Research Depth axis** | Every operation scales with depth, not binary toggle | Jan 30 |
| **Dual space architecture** | User sees clean graph; Voku reasons in hidden workspace | Jan 30 |
| **Bi-temporal model** | Track when beliefs were true vs when recorded | Jan 30 |

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/DESIGN_V03.md` | Complete architecture specification |
| `docs/ARCHITECTURE_DIAGRAMS.md` | Mermaid visual diagrams |
| `docs/STATE.md` | This file — implementation status |
| `docs/CONTINUE.md` | Session continuation prompt |
| `backend/app/services/graph/schema.py` | Kuzu schema definition |
| `backend/app/services/graph/constants.py` | Edge constraints, valid types |
| `backend/app/services/graph/operations.py` | Graph CRUD operations |
| `backend/app/services/providers/` | LLM provider abstraction |
| `backend/tests/test_graph.py` | Graph layer tests (18 passing) |

---

## Next Action

**Vertical slice: text → extraction → graph → visualization**

1. API endpoint: `POST /api/chat` accepting user text
2. LLM extraction: Groq call to extract propositions as JSON
3. Graph write: Create LeafNodes + edges in Kuzu
4. Embedding: Generate + store via sentence-transformers
5. Frontend: React Flow rendering the graph

See `docs/CONTINUE.md` for session pickup.
