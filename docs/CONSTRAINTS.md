# Voku Constraints

**Created:** 2026-02-18
**Purpose:** When two goals conflict, the higher tier wins.

---

## TIER 0: EXISTENCE

1. **Day 3 must be meaningfully better than day 1 because of accumulated context.** This is the minimum existence proof. If the conversation doesn't improve through use, nothing else matters.

2. **The UI is load-bearing, not decorative.** Voku is a thinking environment, not a chatbot with a sidebar. The graph and visual surfaces are part of what makes the product worth using. They ship alongside the conversation, not after.

3. **Real data, not mocks.** The system must work on actual conversations, not contrived demos.

## TIER 1: CAREER

4. **Portfolio value over product completeness.** Clean code, system design thinking, measurable evaluation, justified tradeoffs. A well-documented prototype beats a polished app with no evaluation.

5. **Understanding over speed.** Jaymin is learning this stack. Code he can't explain is debt he can't defend in an interview. Mentor mode is a feature.

6. **Demonstrable.** A working system that proves the thesis late beats a hollow demo on time.

## TIER 2: DEVELOPMENT PROCESS

7. **Spikes before commitments.** Uncertain tech gets a time-boxed experiment (2 hrs max) before adoption. If the spike fails, pivot before building infrastructure around the assumption.

8. **Don't over-classify at ingestion.** Store with minimal metadata (when, what conversation, reasonable name). Interpretation happens at retrieval time through context assembly and projection, not at storage time through taxonomy. This is the ingestion constraint from the "emergent structure" principle.

9. **Tests define done.** No component is complete without passing tests. Tests are the gate. Once they pass, the component is locked.

10. **Vertical slices over horizontal layers.** Don't build all of storage, then all of chat, then all of graph. Build one thin path through all layers and prove it works end-to-end.

11. **No design docs between concept and code.** Architectural decisions happen in spikes and commit messages. If a decision needs documenting, it's an ADR in a single paragraph, not a 400-line treatise.

## TIER 3: TECHNICAL

12. **Local-first, zero-cost default.** Every component works without paid APIs. Paid services are upgrades, not requirements.

13. **Single-file database.** One SQLite file. Portable. `cp voku.db backup.db` is the backup strategy.

14. **Interfaces over implementations.** Every service has an abstract interface. Swapping providers is a config change.

## CONFLICT RESOLUTION

*"Should I write an architecture doc before building?"*
→ Tier 2.10: No. Spike it or build it. The code is the architecture.

*"Should I build the backend first and add UI later?"*
→ Tier 0.2: No. UI is load-bearing. Both ship together.

*"Should I add summary DAG before the basic chat works?"*
→ Tier 2.9: No. Vertical slice first. Chat + storage + basic context + graph skeleton. Then deepen.

*"Should I use Claude Code to generate boilerplate faster?"*
→ Tier 1.5: Only if Jaymin reviews and can explain every line.
