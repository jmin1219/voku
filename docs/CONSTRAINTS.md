# Constraints

> When two design goals conflict, the higher tier wins.

## Tier 0 — Existence

1. **Conversation quality must improve with accumulated context.** Day 3 must be meaningfully better than day 1. If it doesn't improve through use, nothing else matters.
2. **The UI is load-bearing, not decorative.** The phase space and context markers are part of the thinking process — not a dashboard bolted onto a chatbot.
3. **Real data, not mocks.** The system must work on actual conversations, not contrived demos.

## Tier 1 — Design Principles

4. **Don't classify. Annotate.** Store traces with minimal metadata. Annotations are computed, re-extractable, and category-free. No predefined types at the schema level — structure emerges from the data.
5. **Immutable traces, improvable annotations.** Raw conversational content is never modified after creation. Everything computed on top (annotations, connections, embeddings) can be recomputed with better models.
6. **Vertical slices over horizontal layers.** Build one thin path through all layers and prove it works end-to-end before widening.
7. **Tests define done.** No component ships without passing tests.

## Tier 2 — Technical

8. **Local-first, zero-cost default.** Every component works without paid APIs. Paid services are upgrades, not requirements.
9. **Single-file database.** One SQLite file. `cp voku.db backup.db` is the backup strategy.
10. **Interfaces over implementations.** Every service has an abstract interface. Swapping providers is a config change.

## Conflict Resolution Examples

*"Should I add predefined annotation types for common patterns?"*
→ Tier 1.4: No. Let types emerge from extraction.

*"Should I use a graph database for connections?"*
→ Tier 2.9: No. SQLite recursive CTEs handle the query patterns at <10K traces.

*"Should the graph be visible during every conversation?"*
→ Tier 0.2: Only on demand. Research shows permanent split-panel hurts conversation quality.
