# Voku State

> Current position, decisions made, blockers. Updated each session.

**Last Updated:** 2026-02-07 (Phase 0 gate test complete)

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
- **Extraction service** (`services/extraction/`): LLM-based proposition extraction with full schema (including structured_data), 5-layer validation, voice preservation — Phase 0 gate test passed
- **LLM providers** (`services/providers/`): Groq + Ollama abstraction with `complete()` method, system_prompt support, JSON mode, ProviderError handling
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

**Key risk for vertical slice:** Original assumption was that extraction should produce named abstractions ("the fabricator") from single turns. Review revealed these names emerged across 8+ rounds of collaborative dialogue — they're InternalNodes, not LeafNodes. Extraction must target atomic observations that preserve user meaning. Abstraction/naming is a separate operation. If atomic extraction produces clinical summaries despite good few-shot examples, interactive refinement ("AI proposes, human confirms") becomes necessary.

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
| Feb 06 | — | Phase 0 design: extraction targets LeafNodes not abstractions. Few-shot teaches atomic proposition quality, naming/clustering is separate operation. Identified Groq provider gaps (no JSON mode, no system prompt). Created extraction/ directory. |
| Feb 07 | 1.0 | Phase 0 Step 1: Upgraded Provider ABC — `complete()` now accepts keyword-only `system_prompt` and `model` params. Added `ProviderError` custom exception. Groq provider updated with 3-boundary error handling (network, JSON parsing, content extraction). 18 tests still passing. |
| Feb 07 | 2.5 | Phase 0 Steps 2-5: Extraction prompt with full schema (including structured_data), ExtractionService with 5-layer validation, Proposition dataclass. Gate test: 5/5 technical success, voice preservation 80-95%. Prompt improvements: atomic definition, voice preservation strengthening. Retry: 98%+ exact phrase preservation. Decision: proceed to Phase 1 - batch processing + conversational flow will handle refinement. Created vault concept: "privacy-processing tradeoff as architectural primitive". |
| Feb 07 | 2.5 | Phase 1 Steps 1-3: Database lifecycle (lifespan events, idempotent schema), dependency injection system (4 service factories), chat route wired to ChatService, config updates. End-to-end pipeline verified: POST /api/chat/ → extraction → LeafNode creation → response with node IDs. Query script confirms node storage. Identified temporal NLP need (resolve "today" → YYYY-MM-DD). Next: embeddings + semantic dedup. |

---

## Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| **Hybrid batching: per-turn now, batch processing later** | Phase 1: per-turn extraction validates pipeline quickly. Phase 2: batch processing layer adds efficiency (3-10x cost reduction) + clustering (emergent pattern detection). See ADR_001. | Feb 07 |
| **Phase 0 gate passed: proceed to Phase 1** | Extraction quality 80-95% sufficient for pipeline integration. Batch processing will handle fragmentation, conversational flow will handle voice refinement. Perfect extraction in isolation has diminishing returns. Vertical slice approach: build end-to-end, then iterate on quality. | Feb 07 |
| **Privacy-processing tradeoff as architectural primitive** | Research Depth maps to both processing granularity AND privacy boundaries (depth 1-3 local-only, 4-6 hybrid, 7-10 cloud). This abstraction will apply across AI ecosystem as models get more powerful. Justifies bringing back Research Depth. | Feb 07 |
| **Extraction ≠ Abstraction** | Extraction produces LeafNodes (atomic observations). Named abstractions (InternalNodes like "the fabricator") emerge from clustering leaves — separate operation, not single-turn extraction | Feb 06 |
| **Few-shot teaches voice, not naming** | Examples guide atomic proposition quality (preserve user meaning), not concept naming. Naming is human-in-the-loop | Feb 06 |
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
| `docs/ADR_001_BATCHING_STRATEGY.md` | Batching architecture decision rationale |
| `docs/STATE.md` | This file — implementation status |
| `docs/CONTINUE.md` | Session continuation prompt |
| `backend/app/services/graph/schema.py` | Kuzu schema definition |
| `backend/app/services/graph/constants.py` | Edge constraints, valid types |
| `backend/app/services/graph/operations.py` | Graph CRUD operations |
| `backend/app/services/providers/` | LLM provider abstraction |
| `backend/tests/test_graph.py` | Graph layer tests (18 passing) |

---

## Next Action

**Phase 0: ✅ COMPLETE** (Feb 07)

Gate test passed: 5/5 technical success, 3.5/5 excellent voice preservation. Extraction service ready for integration.

**Phase 1: Extraction → Graph Pipeline** (Current - per-turn extraction)

Strategy: Per-turn extraction for fast validation. Batch processing layer deferred to Phase 2 (see ADR_001).

Progress:
1. ✅ Create `POST /api/chat` endpoint accepting user text
2. ✅ Wire extraction service to endpoint
3. ✅ Graph write: propositions → LeafNodes in Kuzu with metadata
4. ⏳ Semantic dedup: cosine similarity > 0.95 before creating nodes (NEXT)
5. ⏳ Basic edge creation: SIMILAR_TO connections between related nodes

Next session: Implement embedding generation, semantic deduplication, and SIMILAR_TO edge creation.

Deferred to Phase 1.5:
- Temporal NLP (resolve "today" → "2026-02-07" with structured_data.event_date)
- Bi-temporal timestamps (recorded_at vs valid_from)

**Phase 2: Batch Processing Layer** (After Phase 1 complete)

Add sophisticated batching: conversation window → single LLM call → clustering → InternalNode proposals → atomic commit. This becomes the demo centerpiece showing emergent pattern detection.

See `voku — development plan.md` Phase 1 for full spec.
See `docs/CONTINUE.md` for session pickup.
