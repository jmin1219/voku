# ADR 002: Meaning at Read-Time, Not Write-Time

**Date:** 2026-02-10
**Status:** Proposed — pending design session (Feb 14-15)
**Context:** Phase 2 (connection layer) was about to add rigid modules + predetermined edge types. This ADR captures the architectural rethink.

---

## The Problem

Phase 2 as planned would:
1. Create ModuleNodes (fitness, career, academics, voku) as fixed categories
2. Assign each LeafNode to a module via CONTAINS edge at extraction time
3. Create SUPPORTS/CONTRADICTS/ENABLES edges via LLM at extraction time

This commits to meaning at write-time. But meaning depends on the question being asked.

"I'm anxious about co-ops" is not intrinsically a career belief that contradicts stated confidence. It might connect to the rest-as-defeat pattern, afternoon murk, or underfueling-driven anxiety. The meaning depends on the retrieval context.

## The Insight

Voku's core promise is tracking belief *evolution*. Evolution is inherently a read-time phenomenon — you can't label how something evolves before you've seen what comes next. Pre-labeling nodes with rigid categories and relationships fights against this.

## The Proposed Architecture: Store Rich, Label Light, Interpret at Read-Time

### Three Modes

**Ingest mode** (user is chatting):
- Store propositions with: embedding, timestamp, raw context, minimal metadata
- Fast, low-latency, conversational
- Light labeling only (e.g., loose domain hint, confidence) — nothing rigid

**Process mode** (user triggers "update" / "go to bed" / scheduled):
- Replay new propositions against full graph
- LLM discovers: clusters, contradictions, evolution chains, emergent themes
- Results stored as **cached analyses** (queryable artifacts), not permanent schema-level edges
- This is where expensive intelligence lives — user isn't waiting

**Query mode** (user asks a question or browses dashboard):
- Pull from warm cache for fast responses
- Fall back to cold storage + live LLM reasoning for novel questions
- Meaning is reconstructed *in context of what's being asked*

### What Changes From Current Design

| Concept | Old (Write-Time) | New (Read-Time) |
|---------|-------------------|------------------|
| Modules | Fixed categories assigned at extraction | Emergent clusters discovered during process mode |
| Edge types | SUPPORTS/CONTRADICTS as schema-level edges | Relationships as cached LLM analyses, rebuildable |
| node_purpose | Rigid enum (observation/belief/pattern/intention/decision) | Loose hint, graceful default, meaning emerges from context |
| "What contradicts what" | Pre-computed edge in graph | Cached analysis rebuilt on each process cycle |

### What Stays The Same

- Extraction pipeline (text → propositions → embeddings → store) ✅
- Semantic dedup (0.95 threshold) ✅
- Bi-temporal model (valid_from/valid_to + recorded_at) ✅
- Ghost persistence (never delete) ✅
- Privacy/sensitivity layer ✅

### Cache Architecture (Sketch)

```
Cold Storage (Kuzu):
  - LeafNodes with embeddings, timestamps, raw context
  - Minimal metadata (loose domain hint, confidence, source_type)
  - Temporal chain (recorded_at ordering)

Warm Cache (rebuilt during process mode):
  - Cluster map: which propositions group together (emergent modules)
  - Contradiction map: which propositions tension against each other
  - Evolution chains: how thinking on a topic changed over time
  - Summary snapshots: compressed state of each cluster
```

Cache is rebuilt incrementally — only new propositions trigger re-analysis of their neighborhood, not full graph recomputation.

## Analogy

Human memory consolidation:
- **Day (ingest):** Experience things, store fragments
- **Sleep (process):** Brain replays, reorganizes, consolidates, finds connections
- **Recall (query):** Reconstruct meaning from consolidated network in context of current need

Voku mirrors this cycle rather than forcing meaning at capture time.

## Open Questions (For Design Session)

1. What minimal metadata DO we need at write-time? (timestamp + embedding is the floor)
2. How are cached analyses stored? (Separate table? JSON blobs? Their own node type?)
3. How does the user interact with emergent clusters vs. manually-defined focus areas?
4. What triggers process mode? (Manual button? Time-based? Threshold of new nodes?)
5. How does privacy/sensitivity constrain process mode? (Local-only nodes skip cloud LLM?)
6. What does the dashboard show from warm cache? What's the "wow" visualization?
7. How do we handle the demo deadline (Mar 31) with this rethink?

## Risk

This is a bigger architectural shift. The current pipeline (ingest) is still valid. But Phase 2 needs redesign before implementation. The risk is spending Friday/Saturday on design instead of code — but building the wrong abstractions is worse.

---

**Next:** Design session Feb 14-15 to resolve open questions and sketch process mode architecture.
