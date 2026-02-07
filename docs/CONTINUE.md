# Voku Continuation Prompt

> Use this to resume work in a new chat session.

---

## Context

**Project:** Voku v0.3 — Personal temporal knowledge graph
**Phase:** Phase 0 — Extraction test (GATE)
**Last Session:** Feb 06, 2026
**Repo state:** Clean — v0.2 stripped, Kuzu 0.11.3, 18 tests passing

## What Was Accomplished (Feb 6)

- Reviewed all 60+ conversations in this project (Dec 12 2025 — Feb 6 2026)
- Mapped every core feature to a documented Claude Desktop failure mode
- Competitive landscape research: Graphiti, Mem0, GraphRAG, PKM tools, context engineering moment
- Critical analysis of research (identified 7 areas where report flatters Voku)
- Deferred 2 features: Research Depth 0-10, Multi-Aspect Embeddings (no documented friction)
- Created comprehensive development plan with learning objectives
- Updated: STATE.md, DESIGN_V03.md, CONTINUE.md, voku.md hub, session log

## Comprehensive Plan (from `brain/concepts/voku — development plan.md`)

### Phase 0: Extraction Test — GATE (~2 hrs)
**Build:**
- Write extraction prompt: conversation turn → structured JSON (proposition, node_purpose, confidence, related_concepts)
- Send 5 real conversation turns from vault sessions to Groq via existing `complete()`
- Evaluate: ≥3/5 must produce propositions you'd want in a graph
- If flat/clinical after 3 prompt iterations → build interactive refinement step

**Learn:**
- Structured LLM output patterns (JSON mode, few-shot prompting)
- Read: Groq docs on JSON mode. Skim GraphRAG paper Section 3 (entity extraction pipeline pattern)

**Gate criteria:** If extraction fails, rethink before building pipeline.

### Phase 1: Extraction → Graph Pipeline (~4-5 hrs)
**Build:**
- `POST /api/chat` endpoint
- Extraction function: text → Groq → JSON → validated propositions
- Graph write: propositions → LeafNodes in Kuzu
- Semantic dedup: cosine similarity check before node creation
- Edge creation: connect new nodes to related existing nodes by embedding similarity

**Learn:**
- Embeddings hands-on: Load bge-base-en-v1.5, embed vault concept titles, compute pairwise similarity
- Kuzu HNSW vector search (v0.11.3 native)
- Study: RAG → GraphRAG → Temporal GraphRAG developmental arc

**Read:** Sentence-transformers model card, Kuzu 0.11.0 release notes (HNSW section), RAG paper abstract + Section 2

### Phase 2: Visualization (~4-5 hrs)
**Build:**
- React Flow graph rendering from `/api/graph` endpoint
- Node styling by type (observations grey, patterns blue, beliefs green, intentions gold)
- Click node → content, timestamps, source conversation

**Learn:**
- React Flow basics (hardcoded graph → live backend data)
- Graph visualization principles (when force-directed breaks down, alternatives)
- Study: PKM → AI visualization evolution (Obsidian graph → Smart Connections → Voku)

### Phase 3: Temporal Demo (~3-4 hrs)
**Build:**
- Process two conversation sets about same topic from different dates
- Visual indicator of belief evolution (color shift, timeline slider)
- Demo scenario: Billy→Voku pivot (Dec planner conversations → Jan knowledge graph conversations)

**Learn:**
- Bi-temporal modeling hands-on (valid_from/valid_to vs recorded_at)
- Study: Context engineering as discipline (Karpathy, Lütke, Anthropic guide, LangChain patterns)
- Read: Zep/Graphiti paper (arXiv 2501.13956) Sections 3-4, Anthropic context engineering guide

### Phase 4: Polish + Portfolio (~4-6 hrs)
**Build:**
- Deploy (Railway/Render), README with screenshots, 2-min demo video, architecture blog post

**Learn:**
- Deployment patterns for AI apps
- Study: Post-Kuzu embedded graph DB landscape (LadybugDB, DuckPGQ, GraphLite)
- Read: G.V() "Yearly Edge 2025" Kuzu section, DuckPGQ blog post

### Deferred (build only if usage reveals need)
- Research Depth 0-10 — no documented friction
- Multi-aspect embeddings — single embedding likely sufficient
- Organization Space — need specific query user space can't answer
- Document Import — demo feedback dependent

## Competitive Positioning (for interviews)

| Competitor | Voku's Difference |
|-----------|-------------------|
| **Graphiti/Zep** | Same temporal architecture, different audience (enterprise agents vs personal beliefs) |
| **Mem0** | Flat key-value memory vs structured belief graph with temporal evolution |
| **GraphRAG** | Static batch processing vs conversational incremental + temporal awareness |
| **Obsidian+AI** | Manual note creation vs automated belief extraction from conversation |
| **Claude memory** | Compressed summaries that mutate vs immutable temporal nodes |

## Key Files

```
# Project
docs/DESIGN_V03.md               # Architecture spec (2 features deferred)
docs/STATE.md                    # Status + feature↔failure mode mapping
backend/app/services/graph/      # Kuzu schema + CRUD (18 tests passing)
backend/app/services/providers/  # Groq + Ollama (working)

# Vault
brain/concepts/voku — development plan.md   # Full roadmap + learning + reading list
brain/concepts/voku.md                       # Hub note (updated Feb 6)
brain/concepts/ref — voku competitive landscape 2026.md  # Research + critical analysis
brain/sessions/2026-02-06_voku-retrospective.md  # Decision record
```

## Run Tests

```bash
cd /Users/jayminchang/Documents/projects/voku/backend
source venv/bin/activate
python -m pytest tests/test_graph.py -v
```

## Resume Command

"Continue Voku Phase 0: write the extraction prompt and test it against 5 real conversation turns from the vault. Read `brain/concepts/voku — development plan.md` for full context. This is the gate — if automated extraction doesn't produce useful propositions, we rethink before building the pipeline."
