# Voku v2 — Carry Forward

**Created:** 2026-02-27  
**Purpose:** Exact mapping of what survives from v1, what gets rebuilt, and the migration sequence.

---

## Git Transition

```bash
# 1. Tag current state
git checkout feat/phase-b-chat-edges
git tag v1-final -m "v1 complete: 181 tests, phase space with InstancedMesh"

# 2. Merge to main, then branch for v2
git checkout main
git merge feat/phase-b-chat-edges
git checkout -b feat/v2-trace-architecture

# 3. v1 docs already archived to docs/archive/v1/

# 4. Preserve v1 database
cp data/voku.db data/voku_v1.db
```

## Backend File Map

### Keep As-Is
| File | Reason |
|------|--------|
| `app/main.py` | FastAPI setup, CORS, lifespan |
| `app/config.py` | Environment config |
| `app/dependencies.py` | Shared singleton pattern |
| `app/services/embedding/` | bge-base-en-v1.5 — unchanged |
| `app/services/providers/` | Groq/Ollama provider abstraction — unchanged |
| `app/services/parser.py` | Markdown conversation parser — unchanged |
| `app/mcp/` | MCP server skeleton — update data source later |
| `requirements.txt` | Add sqlite-vec when needed |
| `tests/fixtures/real/` | 21 conversation fixtures — reuse for v2 testing |

### Refactor (Same File, New Logic)
| File | Changes |
|------|---------|
| `app/routes/chat.py` | Store traces instead of triggering extraction pipeline. Emit retrieval SSE event with trace IDs. |
| `app/services/retrieval.py` | Search traces table instead of propositions. Weight by recency. Pull annotations for enrichment. |
| `app/services/projection.py` | UMAP + DBSCAN on trace embeddings. Same algorithms, new data source. |
| `app/routes/propositions.py` | Rename to `traces.py`. Serve trace + annotation + connection data to frontend. |

### New Files
| File | Purpose |
|------|---------|
| `app/services/annotation.py` | Async annotation extraction from traces. LLM-based, re-runnable. |
| `app/services/storage/trace_storage.py` | CRUD for traces, annotations, connections, resources, embeddings. |
| `app/services/context_assembly.py` | Replaces v1 ContextAssemblyV2. Reads trace graph directly. |
| `scripts/reannotate.py` | Batch re-annotation with model versioning. |
| `scripts/migrate_v1_to_v2.py` | Optional: convert v1 propositions to v2 traces. |
| `migrations/v2_schema.sql` | CREATE TABLE statements for all 5 tables. |

### Drop
| File | Reason |
|------|--------|
| `app/services/extraction/` | Replaced by annotation pipeline |
| `app/services/ingestion.py` | v1 batch ingestion from markdown exports. Traces created in real-time in v2. |
| `app/services/user_model/` | Entire directory (AssignmentService, ExhaleService, UserModelStorage). |
| `app/routes/extract.py` | Replaced by annotation endpoint |
| `scripts/ingest_fixtures.py` | Replaced by new fixture loading for v2 |

## Frontend File Map

### Keep As-Is
| File | Reason |
|------|--------|
| `src/styles/` | Design tokens, IBM Plex, dark/light |
| `src/components/chat/ChatHeader.tsx` | Unchanged |
| `src/components/chat/ChatInput.tsx` | Unchanged (auto-grow textarea) |
| `src/components/phase-space/EdgeMesh.tsx` | Same rendering, new data source |
| `src/components/phase-space/ClusterShell.tsx` | Cluster boundaries (may keep) |

### Refactor
| File | Changes |
|------|---------|
| `src/pages/Workspace.tsx` | Chat-dominant layout. Phase space summoned on demand, not permanent split. |
| `src/components/chat/ChatMessages.tsx` | Add context marker rendering. |
| `src/components/phase-space/NodeCloud.tsx` | Data source: traces. Add node type encoding (shape/border). |
| `src/components/phase-space/CameraController.tsx` | Add 2D ↔ 2.5D transition. Spring-based lerp. Lock free rotation. |
| `src/components/phase-space/Scene.tsx` | Add fog uniform for atmospheric depth in 2.5D mode. |

### New Files
| File | Purpose |
|------|---------|
| `src/components/chat/ContextMarker.tsx` | Inline [1][2] indicators with progressive disclosure. |
| `src/components/chat/TraceDetail.tsx` | Expanded trace view: content, timestamp, annotations, connections. |
| `src/components/phase-space/ThreadPath.tsx` | Parent chain visualization through graph. |
| `src/components/temporal/TemporalDigest.tsx` | AI-generated period summary. |

### Drop
| File | Reason |
|------|--------|
| `src/components/ActiveSummary.tsx` | v1 retrieval display. Replaced by context markers. |
| `src/components/phase-space/DataNode.tsx` | Pre-InstancedMesh reference. Already superseded by NodeCloud. |

## Database Migration

**Recommended: Clean start.** Drop v1 database. Create fresh v2 schema. Re-ingest conversation fixtures through v2 pipeline. Serves as both a pipeline test and a fresh start.

**Alternative: Data migration** via `scripts/migrate_v1_to_v2.py` if continuity matters. Converts each v1 conversation message to a trace, each proposition to an annotation on its source trace, each edge to a semantic connection.

v1 database preserved as `data/voku_v1.db` regardless.

## Test Strategy

v1 tests (181 passing) remain on their branch. v2 tests start fresh:

| Layer | Scope | Target |
|-------|-------|--------|
| Storage | Trace, annotation, connection, resource CRUD | ~30 |
| Embedding | Embed trace, vector search, k-NN | ~10 |
| Annotation | Extraction from real fixtures, type diversity, re-extraction | ~20 |
| Retrieval | Trace retrieval quality, recency weighting, annotation enrichment | ~15 |
| Context Assembly | Format traces for LLM, token budget, relevance ordering | ~15 |
| Projection | UMAP on traces, DBSCAN clustering, data generation | ~10 |
| E2E | Conversation → trace → annotate → retrieve → respond with markers | ~10 |

**Target: ~110 tests for Phases 1–3. ~150+ by demo.**

## Constraints (Updated from v1)

**Tier 0 (Existence)** — unchanged:
- Day 3 must be meaningfully better than Day 1
- UI is load-bearing, not decorative
- Real data, not mocks

**Tier 1 (Career)** — unchanged:
- Portfolio value over product completeness
- Understanding over speed (mentor mode)
- Demonstrable

**Tier 2 (Process)** — one update:
- ~~"Don't over-classify at ingestion"~~ → **"Don't classify at all. Annotate."**
- Vertical slices, spikes before commitments, tests define done — all unchanged

**Tier 3 (Technical)** — unchanged:
- Local-first, zero-cost default
- Single-file database
- Interfaces over implementations
