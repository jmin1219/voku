# Voku State

> *Renamed from BillyAI on Jan 31, 2026*

> Current position, decisions made, blockers. Updated each session.

**Last Updated:** 2026-02-01

---

## Current Phase

**v0.2: Operational Layer** — ✅ COMPLETE (Jan 28)
**v0.3: Knowledge-First Graph** — 🔵 IMPLEMENTATION STARTING

Architecture finalized in `docs/DESIGN_V03.md`. Goal-anchored philosophy clarified. Ready to build.

---

## v0.3 Architecture Summary

**Vision:** Self-understanding as anchor, goals as emergent byproduct. Not a productivity planner — the derivative of that. Surfaces discrepancies between stated intentions and observed patterns.

### Core Innovations

| Innovation | Description |
|------------|-------------|
| **Goal-Anchored Philosophy** | Self-understanding is the anchor; goals emerge from seeing yourself clearly |
| **Intention vs Pattern Detection** | Surfaces gaps between what you say you want and what behavior reveals |
| **Research Depth (0-10)** | Not a toggle—every operation behaves differently based on depth |
| **User + Organization Space** | User sees confirmed nodes; Voku reasons in hidden workspace |
| **Bi-Temporal Model** | valid_from/valid_to (belief time) + recorded_at (system time) |
| **Multi-Aspect Embeddings** | 4 embeddings per node: content, title, context, query |
| **Ghost Persistence** | Never delete—graduated visibility (suggested→faded→archived) |
| **Document Import** | First-class feature solving cold start |

### Technology Stack

| Component | Choice |
|-----------|--------|
| Graph Database | Kuzu (native Cypher, community detection, embedded) |
| Vector Index | Kuzu native |
| Auxiliary Storage | SQLite + FTS5 (conversations, traces, settings) |
| Frontend Graph | React Flow |
| LLM (default) | Groq (fast, free tier) |
| LLM (private) | Ollama (local) |
| Embeddings | bge-base-en-v1.5 (768 dim) |

---

## Implementation Phases

### Phase A: Kuzu Foundation (~4-5 hours)
- [x] Install Kuzu, create `voku.kuzu` database
- [x] User Space schema: ModuleNode, InternalNode, LeafNode
- [x] Organization Space schema: OrganizationNode (type field)
- [x] Edge tables: CONTAINS, SUPPORTS, CONTRADICTS, ENABLES, SUPERSEDES, REFERENCES
- [x] NodeEmbedding table (node_id, embedding_type, embedding)
- [x] Basic CRUD operations with Cypher (create_module, create_leaf_node, get_node)
- [ ] Edge operations (create_edge, get_children)
- [ ] Tests for graph integrity

### Phase B: Auxiliary Storage (~2-3 hours)
- [ ] SQLite schema: conversations, conversation_turns, conversation_fts
- [ ] node_sources table (provenance linking)
- [ ] processing_traces table (full observability)
- [ ] user_settings and processing_config tables
- [ ] Migrate existing v0.2 tables (transactions, merchants)

### Phase C: Processing Pipeline (~5-6 hours)
- [ ] Triage stage (heuristics, no LLM, <100ms)
- [ ] Embed stage (local model, <200ms)
- [ ] Extract stage (LLM proposition extraction, 2-4s async)
- [ ] Connect stage (LLM relationship finding, 2-3s async)
- [ ] Update stage (graph write + WebSocket push)
- [ ] Processing trace logging for every extraction
- [ ] Research depth affects each stage behavior

### Phase D: Multi-Aspect Embeddings (~2-3 hours)
- [ ] content_embedding generation
- [ ] title_embedding generation
- [ ] context_embedding (node + parent summaries)
- [ ] query_embedding (hypothetical questions prompt)
- [ ] Retrieval with weighted combination

### Phase E: Document Import (~2-3 hours)
- [ ] Markdown parser (chunk ~300 tokens)
- [ ] PDF parser integration
- [ ] Obsidian vault import (preserve wikilinks as edges)
- [ ] Module proposal dialog for imported content
- [ ] Bootstrap from existing vault

### Phase F: Chat + Graph UI (~4-5 hours)
- [ ] Left 1/3: Chat interface with depth slider
- [ ] Right 2/3: React Flow graph view
- [ ] Ghost nodes at reduced opacity
- [ ] Module anchors as root nodes
- [ ] WebSocket real-time updates
- [ ] Evolution view toggle

**Total: 20-25 hours**

---

## Session Log

| Date | Hours | Completed |
|------|-------|-----------|
| Jan 30 | — | Architecture finalized, STATE.md synced |
| Jan 31 | — | Goal-anchored philosophy defined, schema updated with node_purpose/source_type/signal_valence |
| Jan 31 | 1.5 | Phase A: Kuzu schema complete (schema.py) |
| | | - 5 node tables: ModuleNode, InternalNode, LeafNode, OrganizationNode, NodeEmbedding |
| | | - 6 edge tables: CONTAINS, SUPPORTS, CONTRADICTS, ENABLES, SUPERSEDES, REFERENCES |
| | | - Data-driven edge generation pattern |
| | | - init_database() tested and working |
| Feb 01 | 1.5 | Phase A: Node CRUD operations complete |
| | | - create_module() with UUID generation, JSON intentions |
| | | - create_leaf_node() with UUID generation |
| | | - get_node() with multi-table search, JSON parsing |
| | | - 6 tests passing (TDD workflow established) |
| | | - Fixed: InternalNode schema syntax error |
| | | - Next: Edge operations (create_edge, get_children) |

---

## Decisions Made (v0.3)

| Decision | Rationale | Date |
|----------|-----------|------|
| **Renamed to Voku** | Professional branding; voku.app domain available | Jan 31 |
| **Goal-anchored philosophy** | Voku is derivative of productivity planning—surfaces self-knowledge that makes productivity possible | Jan 31 |
| **Self-understanding as anchor** | Goals emerge from seeing yourself clearly; inverts typical planner hierarchy | Jan 31 |
| **node_purpose field** | Classify nodes as observation/pattern/belief/intention/decision | Jan 31 |
| **source_type field** | Distinguish explicit (user stated) from inferred (Voku detected) | Jan 31 |
| **signal_valence field** | Track positive/negative/neutral relative to module intentions | Jan 31 |
| **No separate Goal/Plan tables** | Modules + intentions handles goals; plans are InternalNodes with node_purpose='intention' | Jan 31 |
| **Kuzu over SQLite** | Native Cypher, community detection, path algorithms | Jan 30 |
| **Research Depth axis** | Every operation scales with depth, not binary toggle | Jan 30 |
| **Dual space architecture** | User sees clean graph; Voku reasons in hidden workspace | Jan 30 |
| **Bi-temporal model** | Track when beliefs were true vs when recorded | Jan 30 |
| **Multi-aspect embeddings** | Query embeddings enable semantic retrieval beyond literal matching | Jan 30 |
| **Ghost persistence** | Never delete—graduated visibility preserves history | Jan 30 |
| **Document import** | Solves cold start, immediate value from existing vault | Jan 30 |
| **Groq default** | Fast, free tier sufficient for demo | Jan 30 |
| **Full observability** | Processing traces for every extraction | Jan 30 |
| **UUIDs for all node IDs** | Internal generation, semantic title separate | Feb 01 |
| **JSON for intentions field** | json.dumps on write, json.loads on read | Feb 01 |

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/DESIGN_V03.md` | Complete architecture specification (842 lines) |
| `docs/ARCHITECTURE_DIAGRAMS.md` | Mermaid visual diagrams |
| `CONTINUE.md` | Session continuation prompt |
| `backend/app/services/graph/` | Kuzu operations (to create) |
| `backend/app/services/extraction/` | Processing pipeline (to create) |
| `backend/app/services/retrieval/` | Multi-aspect retrieval (to create) |

---

## How to Run (v0.2 — still works)

```bash
# Backend
cd backend
source venv/bin/activate
python -m pytest -v  # 80 tests should pass
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

---

## Next Action

**Phase A: Edge Operations**
1. Write test for `create_edge()` (CONTAINS: module → leaf)
2. Implement `create_edge()` with Cypher
3. Write test for `get_children()`
4. Implement `get_children()`
5. Test SUPPORTS edge type

See `backend/app/services/graph/operations.py` for current stubs.
