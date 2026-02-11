# Voku Project Constraints — Hierarchical Decision Framework

**Created:** 2026-02-11
**Purpose:** When two goals conflict, the higher-ranked constraint wins. Every design decision, scope decision, and time allocation should be traceable to this hierarchy.

---

## TIER 0: EXISTENCE CONSTRAINTS
*If violated, the project has no reason to exist.*

1. **Voku must demonstrate temporal belief tracking that flat memory systems cannot do.** This is the thesis. If the system can't show "your understanding evolved from X to Y, here's the evidence trail," it's just another RAG app. Every component exists to serve this demonstration.

2. **Voku must use real conversational data, not synthetic toy examples.** The claim is that this works on actual human thinking. If it only works on contrived demos, the thesis is unproven. Jaymin's 60+ Claude conversations are the test corpus.

---

## TIER 1: CAREER CONSTRAINTS
*The project serves Jaymin's career — not the other way around.*

3. **Portfolio value over product completeness.** Hiring managers want to see: system design thinking, measurable evaluation, clean code, and the ability to make and justify tradeoffs. A well-documented prototype with honest benchmarks is more valuable than a polished app with no evaluation.

4. **Understanding over speed.** Jaymin is building this to learn (first database project, first LLM pipeline, first graph system). Code he doesn't understand is technical debt he can't explain in an interview. Mentor mode is a feature, not a handicap. If AI generates code, Jaymin must be able to explain every line.

5. **Demonstrable by March 31 target** — but a working system that proves the thesis two weeks late beats a hollow demo on time.

6. **Evaluation results are first-class deliverables.** "Temporal belief accuracy improved X% over flat retrieval" is a sentence that gets interviews. The ablation study and golden test set are as important as the system itself. Build evaluation infrastructure early, not as polish.

---

## TIER 2: DEVELOPMENT CONSTRAINTS
*How work actually gets done.*

7. **Tests before implementation.** No component is "done" without passing tests against its spec. Tests are the gate between milestones. This protects against the design-spiral pattern: once tests pass, the component is locked. Redesign requires a new failing test that justifies the change.

8. **Spikes before commitments.** Any uncertain technology choice (EmbeddingGemma quality, batch import parsing, process mode LLM accuracy) gets a time-boxed spike (2-4 hours max) with real data before being adopted into the architecture. If the spike fails, pivot before building infrastructure around the assumption.

9. **Working vertical slice over horizontal layers.** Don't build "all of storage" then "all of retrieval" then "all of evaluation." Build one thin path through all layers (import 5 conversations → store → retrieve → evaluate) and prove it works end-to-end. Then widen.

10. **Scope is cut from the bottom of the priority list, never the top.** When time runs short: visualization gets simpler (not cut), process mode gets simpler (not cut), evaluation gets smaller (not cut), temporal tracking stays (never cut). The fancy React Flow graph is the first thing to simplify. The temporal accuracy metric is the last.

---

## TIER 3: TECHNICAL CONSTRAINTS
*What "good enough" means for each component.*

11. **Local-first, zero-cost default.** Every component must work without paid APIs. Ollama for embeddings + extraction, SQLite for storage, numpy for vector search. Paid services (Groq, Cerebras) are performance upgrades, not requirements.

12. **Single-file database, portable and backupable.** One SQLite file contains everything. No external services, no Docker dependencies, no setup friction. `cp voku.db voku-backup.db` is the backup strategy.

13. **Interfaces over implementations.** Every service (embedding, extraction, storage, LLM) has a Python abstract interface. Implementations are swappable. Switching from bge-base to EmbeddingGemma is a config change, not a rewrite. This is also an interview talking point.

14. **Minimum viable complexity.** Use the simplest tool that works at personal scale. numpy over sqlite-vec. NetworkX over Neo4j. SQLite over Postgres. FastAPI over Django. Upgrade only when a test demonstrates the simpler tool fails.

---

## TIER 4: LEARNING CONSTRAINTS
*What Jaymin gets out of this beyond the artifact.*

15. **Every architectural decision gets documented with rationale.** ADRs (Architecture Decision Records) exist not just for the project — they're interview preparation. "I chose SQLite over a graph database because..." is a story Jaymin tells in every co-op interview.

16. **The evaluation methodology is transferable knowledge.** RAGAS, DeepEval, golden test sets, ablation studies — these are skills that apply to any AI engineering role. Learning to evaluate AI systems rigorously is as valuable as building them.

17. **The development process itself is portfolio material.** Git history showing spec → test → implement → evaluate progression demonstrates engineering maturity. Commit messages tell the story. The process is the proof.

---

## CONFLICT RESOLUTION EXAMPLES

*"Should I redesign the storage layer again?"*
→ Tier 2.7 (tests gate changes): Only if a failing test justifies it. Architectural elegance alone is not sufficient reason.

*"Should I add a chat interface for the demo?"*
→ Tier 0.1 (must demonstrate temporal tracking): Only if it's necessary to demonstrate the thesis. Batch import + evaluation metrics prove the thesis without a chat UI.

*"Should I spend Saturday on React Flow visualization or evaluation infrastructure?"*
→ Tier 1.6 (evaluation is first-class) beats Tier 2.10 (visualization is first to simplify): Evaluation wins.

*"Should I use Claude Code to generate the SQLite layer faster?"*
→ Tier 1.4 (understanding over speed): Only if Jaymin reviews and can explain every line. Speed without understanding is negative value.

*"EmbeddingGemma spike failed — quality is worse than bge-base on my data."*
→ Tier 2.8 (spikes before commitments): Keep bge-base. The spike's purpose was to answer this question. No sunk cost.

*"Should I build the MCP server or improve temporal accuracy metrics?"*
→ Tier 0.1 (temporal tracking is the thesis) + Tier 1.6 (evaluation is first-class): Improve the metrics. MCP is a delivery mechanism, not the thesis.

*"March 31 is in two weeks and process mode isn't done yet."*
→ Tier 1.5 (March 31 target) vs Tier 0.1 (must demonstrate temporal tracking): Ship what proves the thesis, even if process mode is simplified. A batch script that detects contradictions beats no temporal tracking at all.
