# Voku — Spec

**Author:** Jaymin Chang
**Status:** Research prototype. 271 tests, ~7,600 LOC, ~120 hours.

---

## What It Is

A transparent thinking environment where conversations become timestamped traces in a navigable knowledge graph.

The user talks to an AI about anything — work, learning, decisions, experiences. Each message becomes a permanent trace. Traces connect through semantic similarity, temporal sequence, and intentional links. Over weeks, a navigable graph forms — the structured representation of a person's thinking that any AI system can query.

The user sees what the AI retrieved, how traces connect, and what's missing. The graph is the trust mechanism. The conversation is the input. Everything else is derived.

## Three Axioms

**1. Conversation is cognition.** Traces accumulate as a side effect of thinking out loud. No manual tagging, no categorization.

**2. Emergent structure.** No predefined categories. Connections form from data. Clusters and patterns emerge from density in the graph.

**3. Broad storage, narrow retrieval.** Traces store with minimal metadata. Intelligence happens at retrieval time.


## The Anti-Collapse Principle

Every AI memory system in 2026 collapses its user into a point estimate — a profile, a summary, a set of inferred traits. The system then interacts with its model of the user rather than with the user.

Voku's design is governed by a single test: **does this feature collapse the user into a point estimate, or does it preserve the cloud?**

- Context assembly optimizes for *contextual coherence* (relevant to this moment) rather than *convergence* (an increasingly accurate single model).
- Contradictory traces coexist. The system presents them as evolution, not error.
- Pattern-opinions are scoped to context and timeframe, explicitly revisable.
- The system never says "you are X." It says "in this context, at this time, you expressed X."

---

## Data Model

Five tables. Traces are immutable ground truth. Everything else is computed and replaceable.

```
traces          Immutable conversational records
                id, timestamp, content, conversation_id, parent_trace_id, source

annotations     Computed metadata extracted by LLM (re-extractable, category-free)
                id, trace_id, type, key, value, confidence, extracted_at, extractor

connections     Typed relationships between traces
                source_id, target_id, type (semantic|temporal|intentional|supersedes), weight

resources       External references anchored to introduction moment
                id, trace_id, type, uri, relationship, summary

embeddings      Vector representations (separate for re-embedding with better models)
                trace_id, model, vector, computed_at
```

Key design decisions:
- **No predefined annotation types.** The `type` field is free text populated by the extraction model. Structure emerges from data, not developer intuition.
- **Immutable traces, improvable annotations.** Raw content is never modified. Annotations can be recomputed with better models — the `extractor` field tracks provenance.
- **Single-file SQLite.** At <10K traces, SQLite handles vector search, graph traversal (recursive CTEs), and time-series queries. No server dependency.


---

## Context Assembly Pipeline

How the AI constructs personalized responses from the trace graph:

1. **Embed** the current message (bge-base-en-v1.5, 768 dims).
2. **Retrieve** relevant traces: cosine similarity weighted by recency (exponential decay). Graph expansion follows temporal + intentional connections (1-hop). Intention/commitment annotations boosted 1.3x.
3. **Detect contradictions:** Same annotation key with opposing values across time → evolution cue injected into system prompt.
4. **Assemble context:** Format retrieved traces into system prompt with timestamps and numbered references (~500–800 tokens).
5. **Stream response** with retrieval metadata. Frontend renders trace references as interactive context markers. Phase space highlights corresponding nodes.
6. **Background enrichment:** After response completes, extract annotations and compute temporal connections. This write-back loop enriches the graph for future retrieval.

---

## UI Architecture

**Chat-dominant.** 80%+ of interaction happens in conversation. The phase space is summoned on demand (⌘+Space), not permanently visible.

**Inline context markers.** 1–3 trace references embedded in AI responses (Perplexity-style [1] [2] markers). Hover for excerpt + timestamp. Click for full trace with connections.

**Multi-resolution phase space.** Continuous zoom from individual traces → cluster clouds → broad orientations. No mode switches. UMAP positions from embeddings, hierarchical DBSCAN clustering, k-NN edge topology. InstancedMesh rendering (validated at 869 nodes, 60fps).

**Temporal digest.** Ask "what have I been thinking about this month?" — the AI synthesizes a narrative from the trace graph, not a list. Period summaries stored as system traces, themselves retrievable in future conversations.

**Resurfacing.** Traces from 1 week / 1 month / 1 quarter ago surface naturally in first responses of new sessions when relevant.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, SQLite (WAL mode) |
| Embeddings | bge-base-en-v1.5 via sentence-transformers, numpy cosine search |
| LLM (chat) | Anthropic Claude (streaming) |
| LLM (extraction) | Groq llama-3.3-70b (async annotation extraction) |
| Frontend | React 19, TypeScript, Vite, Tailwind v4 |
| Visualization | Three.js via react-three-fiber, InstancedMesh rendering |
| Deployment | Docker (multi-stage build), Railway |
