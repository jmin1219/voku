# Phase 5: Backend Enrichment — Task Breakdown

**Created:** 2026-03-01
**SPEC ref:** § Build Sequence Phase 5
**Test file prefix:** `test_phase5_` (new files, not patching existing)

---

## Group A: Annotation Wiring + Graph Retrieval

### Task 5.1: Wire annotation extraction as background task in chat.py

**What:** After the stream completes and assistant trace is stored, fire async annotation extraction for both user and assistant traces. Non-blocking — never delays the response.

**Depends on:** `AnnotationExtractionService` (exists, tested), `trace_storage.store_annotation()` (exists), `get_provider()` (exists)

**Changes:**
- `dependencies.py`: Add `annotation_service` singleton (AnnotationExtractionService + get_provider())
- `dependencies.py`: Add `connection_service` singleton (ConnectionService)
- `chat.py`: Add `BackgroundTasks` parameter to `chat()` route. After stream generator completes, schedule `_extract_and_connect()` background task.
- New function `_extract_and_connect(user_trace, assistant_trace, conversation_id)`: extracts annotations for both traces, stores them, computes temporal connection for new traces.

**Acceptance criteria (→ tests in `test_phase5_annotation_wiring.py`):**
1. After a chat round-trip, user trace has annotations stored in DB
2. After a chat round-trip, assistant trace has annotations stored in DB
3. After a chat round-trip, temporal connection exists between user → assistant trace
4. Annotation extraction failure does not affect stored traces or response
5. Background task runs after response is fully streamed (not blocking)

**Async wrinkle:** `AnnotationExtractionService.extract()` is async. FastAPI `BackgroundTasks` runs in the event loop, so `await` works directly. But `generate()` is a sync generator. Solution: don't run extraction inside `generate()`. Use `BackgroundTasks.add_task()` on the route function level, passing the traces after `StreamingResponse` is returned.

**Actual pattern:**
```python
@router.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    # ... setup, store user trace, build context ...
    
    # Collect traces for background processing
    trace_holder = {"user": user_trace, "assistant": None}
    
    def generate():
        # ... stream response ...
        # After stream: store assistant trace
        trace_holder["assistant"] = assistant_trace
    
    response = StreamingResponse(generate(), ...)
    
    # Problem: background_tasks runs after response, but generate() 
    # hasn't run yet when we call add_task. Need a different approach.
```

**Better pattern:** Use Starlette's `background` kwarg on StreamingResponse, or restructure so the background task reads from DB (the traces are already stored by the time generate() finishes). Simplest: at the end of `generate()`, call a sync wrapper that schedules the async work.

---

### Task 5.2: Graph-traversal retrieval (1-hop connection expansion)

**What:** After vector search returns initial traces, expand results by following connections. If trace A is retrieved and has a temporal connection to trace B, trace B becomes a candidate too. This makes retrieval conversation-aware, not just embedding-aware.

**Depends on:** `TraceRetrievalService` (exists), `trace_storage.get_connections_for_trace()` (exists)

**Changes:**
- `trace_retrieval.py`: Add `_expand_via_connections()` method. After initial vector search, for each result, fetch connections (temporal + intentional types). Add connected traces as candidates with a discounted score (e.g., parent_score × 0.7). Deduplicate. Re-rank. Return top-k.
- `trace_retrieval.py`: Add `use_graph` parameter to `retrieve()` (default True).

**Acceptance criteria (→ tests in `test_phase5_graph_retrieval.py`):**
1. Retrieval with `use_graph=True` returns traces connected to vector-matched traces, even if their embeddings are below similarity threshold
2. Connected traces receive a discounted score (original_score × connection_weight × discount_factor)
3. Retrieval with `use_graph=False` behaves identically to current implementation
4. Temporal connections expand retrieval (conversation context)
5. Intentional connections expand retrieval (cross-session threads)
6. Semantic connections do NOT expand retrieval (would just duplicate vector search)
7. Expansion doesn't exceed 2× the requested limit (prevents explosion)
8. Duplicate traces (found by both vector search and graph expansion) keep the higher score

---

### Task 5.3: Compute connections on new traces in background

**What:** When new traces are stored during chat, compute their temporal connections immediately (parent → child). Semantic connections are too expensive per-message — batch those.

**Depends on:** Task 5.1 (background task infrastructure)

**Changes:**
- Inside `_extract_and_connect()`: After annotation extraction, compute temporal connection (user_trace → assistant_trace, and parent → user_trace if parent exists). Do NOT recompute all semantic connections — that's a batch operation.

**Acceptance criteria (→ fold into `test_phase5_annotation_wiring.py`):**
1. After chat, temporal connection exists: parent_trace → user_trace (if parent exists)
2. After chat, temporal connection exists: user_trace → assistant_trace
3. No semantic connections are computed per-message (only batch)

---

## Group B: Contradiction Detection + Hierarchical Clustering

### Task 5.4: Contradiction detection in retrieval

**What:** When context assembly retrieves traces, detect pairs that may contradict each other. High embedding similarity (same topic) + opposing annotation polarity or explicitly conflicting content. Flag these for the LLM to present as evolution, not confusion.

**Depends on:** Task 5.2 (graph retrieval), annotations existing on traces

**Changes:**
- New file: `services/contradiction.py` — `ContradictionDetector` class
- Method `detect(results: list[TraceRetrievalResult]) -> list[tuple[str, str]]`: returns pairs of trace IDs that may contradict
- Strategy: Among retrieved traces, find pairs where (a) cosine similarity > 0.7 AND (b) annotations have opposing signals (e.g., decision type with different values on same key, or belief type with conflicting values)
- `trace_context.py`: When contradictions detected, add temporal ordering cue to system prompt: "Note: traces [2] and [4] address the same topic but reflect different positions taken weeks apart. Present this as evolution."

**Acceptance criteria (→ tests in `test_phase5_contradiction.py`):**
1. Two traces about the same topic with opposing decisions are flagged as contradictory
2. Two traces about the same topic with consistent positions are NOT flagged
3. Two traces about different topics are NOT flagged (even if annotations conflict)
4. Contradiction detection handles zero annotations gracefully (returns empty)
5. Contradictions are ordered chronologically (earlier trace first)
6. System prompt includes temporal evolution cue when contradictions exist

---

### Task 5.5: Hierarchical clustering (fine + orientation)

**What:** Replace single-level DBSCAN with two levels. Fine clusters (eps=0.3) for trace-level grouping. Orientation clusters (eps=0.6) for broad themes. Both computed from embeddings, not UMAP positions.

**Depends on:** `trace_projection.py` (exists, currently uses eps=0.7 on UMAP 3D positions)

**Changes:**
- `trace_projection.py`: Replace single DBSCAN with two passes:
  - Fine: `DBSCAN(eps=0.3, min_samples=3)` on normalized embedding matrix (768d), not UMAP positions. Produces trace-level clusters.
  - Orientation: `DBSCAN(eps=0.6, min_samples=5)` on cluster centroids (average embedding per fine cluster). Produces 3-5 broad regions.
- Return structure adds `orientations` array alongside `clusters`.
- Each fine cluster gets an `orientation_id` field linking to its parent orientation.

**Acceptance criteria (→ tests in `test_phase5_clustering.py`):**
1. Fine clustering produces more clusters than current single-level (eps=0.3 < eps=0.7)
2. Orientation clustering produces 3-7 broad regions from fine cluster centroids
3. Every fine cluster maps to exactly one orientation (or -1 for noise)
4. Clustering runs on embedding space, not UMAP positions
5. Noise traces (cluster=-1 at fine level) are handled — still rendered as unclustered nodes
6. With < 3 traces, returns empty clusters and orientations gracefully

---

### Task 5.6: Cluster metadata generation (LLM labels + summaries)

**What:** For each fine cluster, generate a 3-5 word label and one-sentence summary using the top-5 most central traces. "Central" = closest to cluster centroid in embedding space.

**Depends on:** Task 5.5 (hierarchical clustering), provider (Groq)

**Changes:**
- New file: `services/cluster_metadata.py` — `ClusterMetadataService`
- Method `generate_labels(clusters, traces, embeddings) -> list[ClusterMeta]`
- For each cluster: find 5 traces closest to centroid, send to LLM with prompt asking for label + summary
- `ClusterMeta` dataclass: `cluster_id, label, summary, central_trace_ids`
- Called during `compute_trace_projection()` if LLM provider is available, falls back to keyword extraction (current behavior) if not

**Acceptance criteria (→ tests in `test_phase5_cluster_metadata.py`):**
1. Each cluster gets a label (3-5 words) and summary (1 sentence)
2. Labels come from LLM when provider available
3. Falls back to keyword extraction when LLM unavailable
4. Central traces are selected by embedding distance to centroid, not random
5. Clusters with < 3 traces use keyword fallback (not enough content for LLM)
6. LLM failure on one cluster doesn't break other clusters

**Note:** Use mock provider in tests (same pattern as `test_annotation.py`).

---

## Group C: Resolution API + Pattern-Opinions + Intention Classification

### Task 5.7: Resolution-aware `/api/phase-space` endpoint

**What:** Replace current `/api/traces` route with a new endpoint that returns data structured for multi-resolution rendering: traces with positions, fine clusters with metadata, orientations with aggregate data.

**Depends on:** Tasks 5.5, 5.6

**Changes:**
- `routes/traces.py`: Rename or replace `/api/traces` with `/api/phase-space`
- Response shape:
  ```json
  {
    "traces": [...],          // individual nodes with positions, annotations
    "clusters": [...],        // fine clusters with labels, summaries, centroids
    "orientations": [...],    // broad regions with labels, constituent cluster IDs
    "edges": [...],           // k-NN edges (existing)
    "meta": {...}             // counts, params
  }
  ```
- Orientations include: `id, label, cluster_ids, center, trace_count`
- Frontend can consume any resolution level from the same response

**Acceptance criteria (→ tests in `test_phase5_resolution_api.py`):**
1. `/api/phase-space` returns 200 with traces, clusters, orientations, edges, meta
2. Every trace has a `cluster_id` and `orientation_id`
3. Every cluster has a `label`, `summary`, and `orientation_id`
4. Every orientation has a `label` and `cluster_ids` array
5. Empty database returns valid empty structure (not 500)
6. Response is JSON-serializable (no numpy types leaking)

---

### Task 5.8: Pattern-opinion generation

**What:** Scan annotation clusters to surface recurring tendencies. "You've made 4 decisions about your training program in the last 2 weeks" or "Your commitments about networking are consistently unmet." These are NOT identity labels — they're grounded, scoped, revisable observations.

**Depends on:** Annotations existing, hierarchical clustering

**Changes:**
- New file: `services/patterns.py` — `PatternService`
- Method `detect_patterns(storage) -> list[Pattern]`
- `Pattern` dataclass: `type, description, trace_ids, timeframe, confidence`
- Pattern types:
  - **Frequency**: annotation type + key appearing 3+ times in 2 weeks
  - **Unmet commitment**: commitment annotations without corresponding completion traces
  - **Recurring topic**: topic annotations clustering tightly
- Patterns are computed, not stored. Cached per session.
- Exposed via `/api/patterns` endpoint

**Acceptance criteria (→ tests in `test_phase5_patterns.py`):**
1. Frequency pattern detected when 3+ annotations share same type+key within 2 weeks
2. Frequency pattern includes all contributing trace_ids
3. Pattern description uses provisional language ("~4 decisions about...", not "You always...")
4. Zero annotations returns empty patterns list
5. Patterns are scoped to timeframe (not all-time by default)

**Note:** Unmet commitment detection is the hardest — defer to post-demo if time-constrained. Frequency patterns alone are demo-valuable.

---

### Task 5.9: Intention recognition classification

**What:** When a user trace expresses intent ("I want to...", "I'm trying to...", "My goal is..."), classify it as an intention trace. Intention traces get elevated retrieval weight in future queries on related topics.

**Depends on:** Annotation pipeline (Task 5.1 — annotations need to exist)

**Changes:**
- `services/annotation.py`: Add intention-related types to the extraction prompt examples: `"intention": A stated goal or desired direction (key=the goal, value=context)`
- `trace_retrieval.py`: In `retrieve()`, after scoring, apply intention boost: if a retrieved trace has an annotation of type "intention" or "commitment", multiply its combined score by 1.3x
- The boost is small enough to not override relevance, large enough to surface intentions when topically relevant

**Acceptance criteria (→ tests in `test_phase5_intention.py`):**
1. Traces with "intention" annotations score higher than identical traces without
2. Boost factor is configurable (default 1.3)
3. Intention boost doesn't override low-similarity results (boost only applies to traces already above threshold)
4. Non-intention annotations are unaffected

---

## Deferred to Phase 7 (Demo Polish)

These are in SPEC Phase 5 but have lower demo impact:

- **Resource ingestion endpoint** — File/URL → resource trace. Requires frontend work too. Defer to Phase 7.
- **Unmet commitment detection** — Subset of patterns (Task 5.8). Complex matching logic. Defer.
- **Supersession detection** — LLM-based. Nice-to-have for contradiction presentation. Defer.

---

## Test Strategy

**New test files (one per task group):**
- `test_phase5_annotation_wiring.py` — Tasks 5.1, 5.3
- `test_phase5_graph_retrieval.py` — Task 5.2
- `test_phase5_contradiction.py` — Task 5.4
- `test_phase5_clustering.py` — Task 5.5
- `test_phase5_cluster_metadata.py` — Task 5.6
- `test_phase5_resolution_api.py` — Task 5.7
- `test_phase5_patterns.py` — Task 5.8
- `test_phase5_intention.py` — Task 5.9

**Test-first workflow per task:**
1. Write test file with acceptance criteria as test function stubs
2. Run — all fail (red)
3. Implement minimal code to pass
4. Refactor if needed

---

## Traceability

| SPEC Requirement | Task | Test File |
|-----------------|------|-----------|
| "Wire annotation extraction as asyncio task" | 5.1, 5.3 | test_phase5_annotation_wiring.py |
| "Integrate connections into retrieval (graph traversal)" | 5.2 | test_phase5_graph_retrieval.py |
| "Contradiction detection in retrieval" | 5.4 | test_phase5_contradiction.py |
| "Hierarchical clustering" | 5.5 | test_phase5_clustering.py |
| "Cluster metadata generation" | 5.6 | test_phase5_cluster_metadata.py |
| "Resolution-aware API" | 5.7 | test_phase5_resolution_api.py |
| "Pattern-opinion generation" | 5.8 | test_phase5_patterns.py |
| "Intention recognition" | 5.9 | test_phase5_intention.py |
| "Resource ingestion endpoint" | DEFERRED | — |

---

## Gates

| Group | Gate |
|-------|------|
| A | `pytest test_phase5_annotation_wiring.py test_phase5_graph_retrieval.py` all green |
| B | `pytest test_phase5_contradiction.py test_phase5_clustering.py test_phase5_cluster_metadata.py` all green |
| C | `pytest test_phase5_*` all green. Full suite passes. `/api/phase-space` returns valid multi-resolution response |
