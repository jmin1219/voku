# Voku v2 — Spec

**Created:** 2026-02-27  
**Updated:** 2026-03-02  
**Author:** Jaymin Chang  
**Status:** Phases 0–6 complete (241 tests, ~116 hours). Phase 7 in progress — real-data strategy, temporal digest, demo prep.

---

## What It Is

A transparent thinking environment. The user talks to an AI about anything — work, learning, decisions, experiences. Each message becomes a permanent, timestamped trace. Traces connect through semantic similarity, temporal sequence, and intentional links. Over weeks, a navigable graph forms — the structured representation of the user's thinking that any AI system can query.

The user sees what the AI knows, what it used, and what's missing. The graph is the trust mechanism. The conversation is the input. Everything else is derived.

## Three Axioms

**1. Conversation is cognition.** The user thinks out loud. Traces accumulate as a side effect of a behavior they already want to perform. No manual note-taking, no tagging, no categorization.

**2. Emergent structure.** No predefined categories or taxonomies imposed at design time. Connections form from the data. Clusters, themes, and patterns emerge from density in the graph.

**3. Broad storage, narrow retrieval.** Traces store with minimal metadata (when, what, in what order). Intelligence happens at retrieval time — given this specific query, what's relevant from the full graph?

## Design Philosophy

Find what's necessary, not what's sufficient. Don't add features to chat — find the minimal structure that generates useful emergent properties.

Every AI product in 2026 generalizes by addition (more tools, more integrations, more features). Voku generalizes by removing assumptions: no predefined categories, no separate memory system, no hidden user model. The raw conversational stream, annotated and connected, IS the personal context layer.

### The Anti-Collapse Principle

Every AI memory system in 2026 collapses its user into a point estimate — a profile, a summary, a set of inferred traits. The system then interacts with its model of the user rather than with the user. This is the mechanism by which "being known" degrades into "being boxed."

Voku's design is governed by a single test: **does this feature collapse the user into a point estimate, or does it preserve the cloud?**

- Context assembly optimizes for *contextual coherence* (a local view relevant to this moment) rather than *convergence* (an increasingly accurate single model).
- Contradictory traces coexist. The system presents both without forcing resolution: "in January you leaned toward X, by March you'd shifted toward Y."
- The system never says "you are X." It says "in this context, at this time, you expressed X."
- Pattern-opinions are grounded in specific traces, scoped to context and timeframe, explicitly revisable. Not identity labels.
- Visualization exposes local views at the user's chosen resolution, never the global totality.
- Translation to external tools (via MCP) sends contextually assembled local views, not profiles.

Theoretical grounding: sheaf-theoretic context assembly (Grothendieck's topos theory — local descriptions compatible where they overlap, no global reduction required), quantum cognition (Busemeyer & Bruza — cognitive states are context-dependent, measurement-sensitive, non-commutative), POMDP as simplified technical frame.

---

## Data Model

Five tables. Traces are immutable ground truth. Everything else is computed and replaceable.

### Layer 1: Immutable Ground Truth

```sql
CREATE TABLE traces (
    id              TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,       -- ISO 8601, irreversible anchor
    content         TEXT NOT NULL,       -- raw text, never modified after creation
    conversation_id TEXT,                -- groups traces into sessions
    parent_trace_id TEXT,                -- threading within and across sessions
    source          TEXT NOT NULL,       -- 'user' | 'assistant' | 'resource' | 'system'
    FOREIGN KEY (parent_trace_id) REFERENCES traces(id)
);
```

Traces are permanent. What was said, when, in what order.

The `parent_trace_id` encodes the full tree structure:
- Within a session: trace₁ → trace₂ → trace₃ (chain)
- Branching: trace₂ → trace₃ AND trace₂ → trace₄ (fork)
- Cross-session threads: intentional connections in the connections table
- Path traversal: recursive CTEs walking parent chain (sub-millisecond at <10K traces)

No stored path arrays. The tree is implicit in parent links.

### Layer 2: Computed Annotations

```sql
CREATE TABLE annotations (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,
    type            TEXT NOT NULL,       -- free text: 'measurable' | 'commitment' | 'decision' | 'emotion' | 'topic' | ...
    key             TEXT,                -- what was measured/committed/decided/felt/discussed
    value           TEXT,                -- the extracted value
    confidence      REAL,
    extracted_at    TEXT NOT NULL,
    extractor       TEXT NOT NULL,       -- model/version that produced this
    FOREIGN KEY (trace_id) REFERENCES traces(id)
);
```

No annotation type is predefined at the schema level. The `type` and `key` fields are free text populated by the extraction model. If a user journals about cooking, the system produces `{type: "measurable", key: "recipe_time"}` without any schema change.

Annotations are re-extractable. When the extraction model improves, re-annotate all traces. The `extractor` field tracks provenance.

Speech act types (Austin/Searle) guide extraction but aren't hardcoded:
- **Asserting** → annotations about states of the world (measurables, facts, beliefs)
- **Committing** → annotations about future actions (commitments, plans, goals)
- **Directing** → typically not annotated (requests to the AI, not self-knowledge)
- **Expressing** → annotations about emotional or evaluative states
- **Declaring** → annotations about decisions, definitions, renamings

### Layer 3: Relationships

```sql
CREATE TABLE connections (
    source_id       TEXT NOT NULL,
    target_id       TEXT NOT NULL,
    type            TEXT NOT NULL,       -- 'semantic' | 'temporal' | 'intentional' | 'supersedes'
    weight          REAL,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES traces(id),
    FOREIGN KEY (target_id) REFERENCES traces(id),
    PRIMARY KEY (source_id, target_id, type)
);
```

- **semantic**: computed from embedding cosine similarity (k-NN). Ambient topology.
- **temporal**: sequential traces in a session. Conversation flow.
- **intentional**: user or system links traces across sessions.
- **supersedes**: extracted relationship — a later trace replaces an earlier understanding.

Semantic connections recompute when embeddings change. Intentional connections are permanent. Supersession is extracted and improvable.

### Layer 4: External References

```sql
CREATE TABLE resources (
    id              TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,       -- the trace where this was introduced
    type            TEXT NOT NULL,       -- 'paper' | 'transcript' | 'url' | 'file' | 'image'
    uri             TEXT,
    relationship    TEXT DEFAULT 'encountered',  -- 'encountered' | 'understood' | 'applied' | 'revised' | 'abandoned'
    summary         TEXT,                -- LLM-generated on ingest
    FOREIGN KEY (trace_id) REFERENCES traces(id)
);
```

Resources are always anchored to the trace where they were introduced — the moment of engagement, not a floating reference.

### Layer 5: Embeddings

```sql
CREATE TABLE embeddings (
    trace_id        TEXT PRIMARY KEY,
    model           TEXT NOT NULL,       -- 'bge-base-en-v1.5'
    vector          BLOB NOT NULL,
    computed_at     TEXT NOT NULL,
    FOREIGN KEY (trace_id) REFERENCES traces(id)
);
```

Separate table. When a better embedding model ships, re-embed everything. The `model` field tracks provenance.

### Why SQLite

At the expected scale (<10K traces after a year of daily use), SQLite handles all query patterns: vector search (sqlite-vec extension), graph traversal (recursive CTEs), time-series (standard ORDER BY with WHERE on annotations), full-text search (FTS5 on traces.content). Single file. Local-first. No server dependency.

---

## UI/UX Architecture

Design decisions grounded in HCI research (AAAI 2025 citation study N=303, EchoMind CSCW 2025, split-attention effect literature, IEEE TVCG node-link comprehension studies, calm technology principles) and the anti-collapse principle (sheaf-theoretic context assembly, quantum cognition).

### Core Interaction Model

The primary experience is a conversation that feels uncannily rich. The user doesn't think "this AI has a good memory" — they think "this AI *gets* me." The system's knowledge is never the subject; the user's thinking is. Everything in the UI serves this inversion.

### Principles

**Chat-dominant.** 80%+ of interaction happens in conversation. Secondary surfaces are summoned on demand, not permanently visible.

**Inline context, not sidebar.** 1–3 trace references embedded in the AI response (Perplexity-style numbered markers). Progressive disclosure: marker → excerpt → full original trace. Research shows 1 citation equals 5 for trust (AAAI 2025), and <10% of users verify citations. Build for presence-as-signal.

**Multi-resolution, not multi-mode.** The phase space is a continuous zoom from individual traces through cluster clouds to broad orientations. No modal switches. The representation adapts fluidly to the user's chosen resolution level.

**Never claim completeness.** At every zoom level, edges fade to transparency at the boundary. No hard borders. The graph never claims to be the whole picture.

### Surface 1: Conversation Stream (Primary)

Full-width chat, centered at 720px max. No permanent split panel. Fast for quick interactions, deep for extended sessions.

**Context markers** appear inline in AI responses. Small numbered indicators [1] [2] linking to specific retrieved traces. On hover: trace excerpt + relative timestamp + source label. On click: full original trace with connections. Collapsed by default. Maximum 3 per response. Connection type subtly encoded in visual differentiation (semantic vs temporal vs intentional retrieval). [BUILT — basic version working, connection type encoding TODO]

**Trace creation** is invisible. Messages store as traces on send. Annotation extraction runs asynchronously — never blocks the conversation. [BUILT]

**Contradiction surfacing.** When context assembly retrieves conflicting traces, the AI presents them as evolution: "in January you leaned toward X, by March you'd shifted toward Y." Context markers for contradictory traces show a subtle temporal arc indicator — a visual cue that these traces span a range, not a point. [BUILT — backend contradiction detection + evolution cue in system prompt. Visual arc indicator TODO]

**Resource ingestion** through conversation. Drop a file, paste a URL. It becomes a resource trace anchored to this moment. UI shows a small resource chip above the input. [TODO]

**Intention recognition.** When the user expresses intent ("I want to explore...", "I'm trying to decide..."), the system elevates these traces in future retrieval. No UI change — backend classification. Over time the system surfaces gaps between stated intention and actual behavior (YNAB principle: hold intentions, surface alignment/divergence). [BUILT — 1.3x intention boost for traces with intention/commitment annotations]

**Conversation continuity.** New sessions don't recap. The system *uses* prior context naturally and context markers show where it came from. The user feels continuity without being told about it. [BUILT — natural consequence of trace-based retrieval]

**Immersive reading mode.** Toggle: user messages compress to thin summary lines during long AI responses. Conversation feels like a thinking environment, not a chat app. Default off. [DEFERRED]

### Surface 2: Phase Space (On Demand — Multi-Resolution Cloud)

Summoned via keyboard shortcut (⌘+Space). Slides in from right as collapsible split or full-screen overlay with chat accessible beneath (tabbed). Dismissed returns to full-width chat. Remembers last zoom level and position.

**The phase space is a resolution-continuous spatial environment.** Not a graph view with mode switches. The user zooms continuously and the representation adapts.

#### Trace Level (Closest Zoom)

Individual traces as discrete nodes. UMAP x,y positions from embeddings. Labels readable. 15–20 nodes visible in the focused neighborhood (EchoMind pattern), remainder as dim ambient cloud.

- Node shape encodes source type: circles (user), rounded rectangles (assistant), diamonds (resource), hexagons (decision)
- Size from recency + connectivity
- Color from recency: warm gold/amber (active) → cool slate/blue-grey (dormant)
- Retrieval glow: retrieved traces flash gold accent during conversation, then fade
- Connections visible: semantic (solid), temporal (thin), intentional (distinct), contradictory (dashed/two-toned)
- Thread paths: parent chain rendered as connected path on selection
- Click a trace → read content, see annotations, see connections

#### Cloud Level (Mid Zoom)

As the user zooms out, individual traces fade and merge into cluster clouds. DBSCAN clusters (computed from embeddings at epsilon=0.3) become the visible units.

- Each cloud has an AI-generated label (3–5 words) and one-sentence summary, computed from the top-5 most central traces in the cluster
- Clouds are soft-edged, slightly translucent, sized by trace density
- Color encodes recency: warm clouds are actively developing, cool clouds are dormant
- Inter-cluster connections visible: aggregate relationships computed from cross-cluster connection density
- Click a cloud → it expands, zooming into constituent traces. Summary appears: "~47 traces about career exploration. Formed over last 3 weeks."
- Can ask the AI about a cloud — triggers temporal digest for that cluster

#### Orientation Level (Maximum Zoom-Out)

Clouds merge into 3–5 large regions representing the broadest themes. Computed by hierarchical clustering (DBSCAN at coarser epsilon=0.6) or LLM synthesis.

- Regions look like terrain: large landmasses with varying elevation (density/recency), coastlines where themes blend, open water where gaps exist
- Very soft edges, high transparency, large labels, atmospheric
- Click a region → zooms to cloud level within that region
- AI can generate orientation summaries on request

#### Zoom Behavior

Zooming is **continuous, not modal**. No "switch to cluster view" buttons. Pinch/scroll and the resolution shifts fluidly:
- Trace level: individual nodes, sharp edges, full opacity, readable text
- Cloud level: soft edges, slight transparency, labels only, collective identity
- Orientation level: very soft edges, high transparency, large labels, terrain-like

The transition is smooth interpolation. Individual traces dissolve into clouds, clouds dissolve into orientations. Zoom back in and they re-emerge. Same underlying data, resolution-adaptive representation.

#### Interaction Across Levels

**EchoMind focus** applies at every level. Select anything — trace, cloud, region — and its neighborhood expands to readable detail. Everything else compresses to ambient background.

**Retrieval visualization during chat.** When the AI responds with context markers, the phase space (if open) shows activity:
- Trace level: specific retrieved nodes glow gold
- Cloud level: relevant clusters pulse subtly
- Orientation level: relevant regions warm

The user glances at the phase space and sees *where* context came from spatially.

**Decay is visible.** Traces not retrieved or connected to new thinking for a long time shrink slightly and cool in color. The graph shows what's fading. The user can re-engage a dimming region or let it fade.

**Contradictions are visually distinct.** Traces with opposing content polarity (high similarity but inverted sentiment/annotations) render their connection as dashed or two-toned. Not errors — "where your thinking was in tension."

**The system never auto-labels.** Labels generate on click/hover, presented as provisional: "~47 traces about career exploration" not "Your Career." The tilde does anti-collapse work.

### Surface 3: Temporal Digest (Integrated)

Not a separate view. A capability invoked from chat or phase space.

**In chat:** Ask "what have I been thinking about this month?" or "how has my thinking about X evolved?" The AI synthesizes a temporal *narrative* (not a list) from the trace graph. Includes context markers pointing to anchor traces. The user can follow any thread deeper.

**In phase space:** Time slider at bottom. Drag and watch clouds form, dissolve, shift over time. Animated topology change — the "zooming out in time" complement to "zooming out in space."

**Period summaries.** Auto-generated weekly/monthly digests stored as system traces in the graph, themselves retrievable. "Week of Feb 24: Major architectural pivot from propositions to traces. 12 sessions, ~14 hours. Key decisions: SQLite retained, 3D dropped, chat-first confirmed." First-class nodes that future retrieval can surface.

**"On This Day" resurfacing.** When traces from 1 week / 1 month / 1 quarter ago remain relevant, the system subtly surfaces them in its first response of a new session — as contextual references, not notifications. The user feels temporal depth without being shown a timeline.

**Resurfacing prompts.** Periodic contextual prompts in conversation surfacing relevant traces from weeks or months prior.

---

## Context Assembly

How the AI uses the trace graph to construct personalized responses. Implements the Context Constructor → Updater → Evaluator pipeline (aligned with Xu et al. 2025 "Everything is Context" architecture).

1. **Embed** the current message.
2. **Retrieve** relevant traces: vector search weighted by recency (exponential decay). Graph expansion follows temporal + intentional connections (1-hop). Intention/commitment traces boosted 1.3x.
3. **Detect** contradictions: same annotation key with opposing values across time → evolution cue injected into system prompt.
4. **Assemble** context: format retrieved traces into system prompt with date, identity, and numbered references. Token budget: ~500–800 tokens.
5. **Stream** response with metadata: first line is JSON with conversation_id + retrieval_ids. Frontend renders retrieval IDs as context markers. Phase space highlights corresponding nodes.
6. **Evaluate** (background): after response completes, extract annotations from both user and assistant traces, compute temporal connections. This is the "write-back" loop that enriches the graph for future retrieval.

---

## Annotation Pipeline

Asynchronous, non-blocking, re-runnable. Implemented in `background.py` + `annotation.py`.

**When:** After each chat message (both user and assistant traces). Runs as Starlette BackgroundTask — does not block the AI response.

**How:** Groq LLM call (llama-3.3-70b-versatile, json_object mode) with trace content + up to 4 recent conversation context traces. Extracts annotations based on speech act analysis. No predefined categories. Response is a JSON object wrapping an array of annotations — parser unwraps both bare arrays and dict-wrapped arrays (Groq's json_object mode forces object wrapping).

**Output:** Zero to five annotations per trace. Types emerge from content — measurables, commitments, emotions, topics, decisions, beliefs, questions.

**Downstream consumers:** Contradiction detection (same key, different values), pattern detection (frequency analysis), intention boost (1.3x for intention/commitment annotations in retrieval), cluster metadata (LLM labels from annotation-rich traces).

**Re-extraction:** `python -m scripts.reannotate --model <model> --since <date>` re-annotates traces with a specified model. Old annotations preserved with their `extractor` tag.

---

## Build Sequence

### Phase 0: Environment Setup ✅
- Tag current branch as `v1-final`
- Create `feat/v2-trace-architecture` off main
- Archive v1 docs, preserve v1 database
- Create v2 schema migration
- Verify v1 tests isolated on their branch

### Phase 1: Trace Pipeline ✅
- Trace storage: conversation endpoint stores messages as traces with parent links
- Embedding: embed each trace on creation
- Retrieval: vector search on traces, return top-k weighted by recency
- Context assembly: format retrieved traces for LLM
- **Gate:** Conversation quality improves with accumulated trace context

### Phase 2: Annotation Pipeline ✅
- Async annotation service
- Annotation types emerge from extraction (no hardcoded types)
- Structured data extraction (measurables, commitments, emotions, topics)
- Re-annotation script for batch processing

### Phase 3: Connections ✅
- Semantic connections (k-NN on embeddings)
- Temporal connections (auto-generated within sessions)
- Intentional connections (API endpoint)
- Supersession detection (LLM-based)

### Phase 4: Frontend — Chat + Context Markers ✅
- Wire chat to trace-based backend
- Inline context markers with progressive disclosure
- Resource ingestion through chat

### Phase 5: Backend Enrichment ✅ (Mar 1)
- Wire annotation extraction as asyncio task in chat.py
- Integrate connections into retrieval (graph traversal, not just flat vector search)
- Contradiction detection in retrieval (embedding similarity + annotation polarity inversion)
- Intention recognition (classify intent traces, elevate in future retrieval)
- Hierarchical clustering: DBSCAN at epsilon=0.3 (fine clusters) + epsilon=0.6 (orientations)
- Cluster metadata generation: LLM labels + summaries from top-5 central traces per cluster
- Pattern-opinion generation: scan annotation clusters for recurring tendencies
- Resolution-aware API: `/api/phase-space` returning trace/cluster/orientation data

### Phase 6: Frontend — Multi-Resolution Phase Space ✅ (Mar 1)
- Phase space container: summonable (⌘+Space), collapsible split
- Trace-level rendering: InstancedMesh, recency color, EchoMind focus
- Cloud-level rendering: cluster shells, k-NN edges
- Retrieval glow: sync with chat context markers
- OrbitControls + focus animation
- NodeLabels (hover-only)
- Unified dark theme

### Phase 7: Temporal Digest + Demo ← CURRENT
See `docs/TASKS_PHASE7.md` for detailed task breakdown.

- **Content strategy (revised Mar 2):** Real data from daily Voku use replaces synthetic persona (Mina). Multi-domain conversations (career, academics, training, personal) produce thematic cluster separation organically.
- Period summary generation (narrative, not list)
- Period summaries stored as system traces in graph
- "On This Day" resurfacing in first response of new sessions
- Demo deployment (Dockerfile + Railway)
- Demo narrative script + rehearsal

**Estimated total: ~14–18 sessions. Currently at ~116 hours across 30+ sessions.**

---

## Demo Narrative

1. **Open.** Clean chat. No onboarding. The system has been accumulating traces from weeks of daily use across multiple domains (career, academics, training, personal).
2. **Ask something that spans sessions.** "What have I been going back and forth on?" Rich response referencing traces across weeks. Context markers [1] [2] [3] show specific moments. Hover one — see the original thinking. Contradictions presented as evolution.
3. **Summon the phase space.** ⌘+Space. Clouds appear — 6–7 clusters, warm and cool, different sizes. Referenced clusters pulsing gold.
4. **Zoom into a cloud.** Click the career cluster. It expands — individual traces, connections, thread paths. Some warm (recent), some cool (weeks old). A dashed connection shows where thinking was in tension.
5. **Zoom all the way out.** Pinch out. Traces dissolve into clouds. Clouds merge into 3–4 orientations. The topology of a mind's recent history at a glance. One region warm and dense (Voku). One moderate (career). One cooling (early coursework).
6. **Time slider.** Drag the temporal control. Watch clouds form, grow, shift over two months. See the proposition → trace pivot — a cluster splits and reforms.
7. **Drop a resource.** Paste a paper URL. New node appears near the relevant cluster. The graph grows in real time.
8. **Temporal digest.** "Summarize my February." AI generates a narrative of how thinking evolved, what decisions were made, what's unresolved. Context markers throughout.
9. **Close.** "Three primitives — traces, connections, resources. The graph emerges from conversation. The chat feels like an AI that knows you. The phase space shows the topology of your thinking at any resolution. And the system never tells you who you are — it holds the cloud and lets you explore it."

---

## Portfolio Value

- **System design:** Five-table schema generating emergent structure from minimal primitives. Anti-collapse principle as design test. Decisions grounded in cross-disciplinary research (sheaf theory, quantum cognition, POMDP, ecological dynamics, HCI).
- **Context engineering:** Implements the full context engineering pipeline (Constructor → Updater → Evaluator per Xu et al. 2025) through trace retrieval, streaming context assembly, and annotation extraction with contradiction detection. Bottom-up emergence from three primitives vs. top-down governance infrastructure. Benchmarkable against MemoryArena.
- **Full-stack implementation:** FastAPI + SQLite + React + Three.js. 241 tests, ~7,600+ LOC. Multi-resolution phase space with InstancedMesh rendering. Chat-first with inline context markers. Real-time retrieval visualization.
- **HCI research integration:** Design decisions backed by empirical evidence (AAAI 2025, EchoMind CSCW 2025, split-attention literature, calm technology). Theoretical grounding for *why* findings hold (anti-collapse principle).
- **Product thinking:** Competitive analysis against Claude memory, ChatGPT memory, Kin, Dot, Mem0, Letta. Addresses "context rot" (Chroma Research) through temporal digest and visual recency encoding. Clear architectural differentiation: the only system that makes the AI's context transparent and navigable.
- **Novel design principle:** "Known without being boxed" — formalized through sheaf theory and quantum cognition. Every feature passes the test: does this collapse or preserve the cloud?

---

## Future Design Considerations

### Agent Reasoning Traces

The current `source` field on traces supports `'user' | 'assistant' | 'resource' | 'system'`. Assistant traces capture what the AI *said*. What's missing: what the AI *considered*.

When an AI agent reviews code and says "this retrieval weighting is wrong because X," the reasoning behind that conclusion — alternatives weighed, uncertainties, why option A beat option B — is valuable context for future sessions. Currently this reasoning evaporates when a session ends. The next session re-derives it from scratch, or derives something slightly different because the context assembled differently.

Agent reasoning traces would capture this: `source: 'agent_reasoning'`, linked to the traces they reference. The transparency layer already shows "what the system used" — this extends it to "how the system thought." The graph would surface prior reasoning when similar code or decisions come up again, rather than forcing re-derivation every session.

This also surfaces a deeper design problem: the CLAUDE.md file in this repo is a manual workaround for this gap — humans encoding an AI's reasoning conclusions into a static file so the next AI session can skip re-derivation. If the trace graph captured agent reasoning natively, that file becomes unnecessary. The graph replaces the document.

Not in scope for v2 demo. But the schema supports it without modification — traces with `source: 'system'` or a new source type, annotated like any other trace.

---

*The framework is the intellectual contribution. The anti-collapse principle is the design contribution. This product is one expression of both.*
