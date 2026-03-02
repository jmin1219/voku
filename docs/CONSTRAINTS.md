# Voku Constraints

**Created:** 2026-02-18  
**Updated:** 2026-03-02 (v2 — confirmed stable through Phase 6)  
**Purpose:** When two goals conflict, the higher tier wins.

---

## TIER 0: EXISTENCE

1. **Day 3 must be meaningfully better than day 1 because of accumulated context.** Minimum existence proof. If conversation quality doesn't improve through use, nothing else matters.

2. **The UI is load-bearing, not decorative.** Voku is a thinking environment, not a chatbot with a sidebar. The phase space and context markers are part of what makes the product worth using.

3. **Real data, not mocks.** The system must work on actual conversations, not contrived demos.

## TIER 1: CAREER

4. **Portfolio value over product completeness.** Clean code, system design thinking, measurable evaluation, justified tradeoffs. A well-documented prototype beats a polished app with no evaluation.

5. **Understanding over speed.** Code that can't be explained is debt that can't be defended in an interview. Mentor mode is a feature, not a limitation.

6. **Demonstrable.** A working system that proves the thesis late beats a hollow demo on time.

## TIER 2: DEVELOPMENT PROCESS

7. **Spikes before commitments.** Uncertain tech gets a time-boxed experiment (2 hrs max) before adoption.

8. **Don't classify at all. Annotate.** Store traces with minimal metadata. Annotations are computed, re-extractable, and category-free. No predefined types at the schema level. Structure emerges from the data, not from developer intuition.

9. **Tests define done.** No component is complete without passing tests.

10. **Vertical slices over horizontal layers.** Build one thin path through all layers and prove it works end-to-end.

11. **Immutable traces, improvable annotations.** Raw conversational content is sacred — never modified after creation. Everything computed on top of traces (annotations, connections, embeddings) can be recomputed with better models.

## TIER 3: TECHNICAL

12. **Local-first, zero-cost default.** Every component works without paid APIs. Paid services are upgrades, not requirements.

13. **Single-file database.** One SQLite file. Portable. `cp voku.db backup.db` is the backup strategy.

14. **Interfaces over implementations.** Every service has an abstract interface. Swapping providers is a config change.

## CONFLICT RESOLUTION

*"Should I add predefined annotation types for common patterns?"*  
→ Tier 2.8: No. Let types emerge from extraction. If "measurable" appears in 80% of training traces, the model learns that — you don't hardcode it.

*"Should I build the phase space before the trace pipeline works?"*  
→ Tier 2.10: No. Vertical slice first. Trace storage + retrieval + context assembly. Then layer visualization on top.

*"Should I use a graph database for connections?"*  
→ Tier 3.13: No. SQLite recursive CTEs handle the query patterns at <10K traces. Single file stays.

*"Should the graph be visible during every conversation?"*  
→ Tier 0.2: Only on demand. Research shows permanent split-panel hurts conversation quality. The graph is load-bearing when summoned — not when forced.
