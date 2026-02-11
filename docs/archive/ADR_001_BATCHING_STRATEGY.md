# ADR 001: Batching Strategy for Extraction Pipeline

**Status:** Accepted  
**Date:** 2026-02-07  
**Context:** Phase 1 implementation - deciding when batching occurs in extraction → graph pipeline

---

## Problem

Batch processing is core to Voku's value proposition (efficiency + emergent pattern detection). Two architectural approaches:

**Strategy A: Batch BEFORE graph creation**
- Accumulate conversation turns → single LLM call → batch write to graph

**Strategy B: Batch AFTER graph creation** 
- Per-turn extraction → immediate graph write → batch clustering later

Where should batching occur to maximize:
1. Extraction quality (voice preservation)
2. Performance (cost, latency)
3. Clustering legitimacy (pattern detection)
4. Implementation speed (MVP timeline)

---

## Analysis

### Voice Preservation & Quality
**Winner: Strategy A**
- LLM sees full conversation context (cross-turn references)
- Maintains narrative flow ("continuing that thought...")
- User corrections refine earlier extractions
- Phase 0 showed 80-95% quality on isolated text; multi-turn context improves this

### Performance & Cost
**Winner: Strategy A (3-10x cheaper)**
- 1 LLM call vs N calls per turn
- Single embedding generation pass
- Single atomic transaction
- Major talking point: "Optimized LLM costs through batching"

### Clustering & Abstraction
**Winner: Strategy A (enables core differentiator)**
- Named abstractions ("the fabricator") emerged across 8+ dialogue rounds
- Clustering requires batch context to find patterns
- Batch enables atomic operation: LeafNodes + InternalNodes + edges together
- **This is the architectural primitive that enables abstraction discovery**
- Differentiator vs Claude Desktop's lossy compression

### User Experience
**Strategy A:** Session-based (accumulate → process → reflect)
- Aligns with "cognitive prosthetic" positioning
- Batch trigger: time-based, message count, or explicit "process this"
- Processing: 2-5 seconds
- Results: atomic observations + proposed clusters for confirmation

**Strategy B:** Chat-based (instant feedback per turn)
- Feels more conversational
- Nodes appear immediately
- Background clustering less cohesive

**Verdict:** Voku as reflection tool (not chat) → batching fits session mental model

### Implementation Complexity
**Winner: Strategy A (simpler)**
- Single transaction, clear error boundaries
- No staged node state management
- Easier to test and reason about

---

## Decision

**Build hybrid approach:**

### Phase 1 (Current): Strategy B - Per-Turn Extraction
**Why:** Validate pipeline end-to-end quickly
- Single turn → extraction → graph node → visible
- Proves: extraction quality, graph operations, semantic dedup, rendering
- Enables frontend development (need nodes to render)
- Faster to implement (less state management)

**Implementation:**
```python
POST /api/chat
  → extract_single_turn(text)
  → semantic_dedup(propositions)
  → create_leaf_nodes(unique_propositions)
  → return node_ids
```

### Phase 2 (After visualization works): Strategy A - Batch Processing
**Why:** Sophisticated layer becomes demo centerpiece
- Visual proof: scattered nodes → clusters form → InternalNodes appear
- Demonstrates: performance optimization, graph algorithms, system architecture
- Interview talking point: "Built simple version first, added sophistication"

**Implementation:**
```python
POST /api/batch/process
  → extract_batch(conversation_window)  # 1 LLM call, full context
  → cluster_propositions(embeddings, graph_structure)
  → propose_internal_nodes(clusters)
  → return { leaf_nodes, proposed_clusters, confidence_scores }

POST /api/batch/commit  # After user confirmation
  → atomic transaction (nodes + edges)
```

---

## Consequences

### Positive
- Fast validation of core extraction quality (Phase 1)
- Proves graph operations work before adding complexity
- Batch layer becomes sophisticated talking point (Phase 2)
- Clustering demonstrates "emergent pattern detection" differentiator
- Clear evolution: simple → sophisticated (good narrative)

### Negative
- Phase 1 won't show full Voku value (per-turn = scattered nodes)
- Some duplicate work (rewrite extraction flow for batching)
- Deferred cost optimization (N LLM calls expensive in Phase 1)

### Mitigations
- Phase 1 is prototype to validate assumptions
- Frontend visualization makes batch processing value visible
- Can run Phase 1 with limited conversation turns (cost contained)
- Clear documentation prevents rework (this ADR)

---

## Related Decisions

- **Phase 0 extraction design:** Atomic propositions (LeafNodes) vs named abstractions (InternalNodes) are separate operations
- **Research Depth as privacy-processing primitive:** Maps to batch granularity (local vs cloud processing)
- **Ghost persistence:** Never delete nodes → batch clustering can revisit historical data

---

## References

- `docs/STATE.md` - Phase 1 implementation plan
- `docs/DESIGN_V03.md` - Architecture specification
- `backend/app/services/extraction/` - Phase 0 extraction service
- Vault: `brain/concepts/privacy-processing tradeoff.md` - Research Depth rationale
