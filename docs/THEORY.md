# Voku — Theoretical Foundations

**Created:** 2026-02-20
**Status:** Living document. Cross-domain connections that inform Voku's architecture.
**Nature:** This document is theoretical. It traces the ideas behind design decisions, not the decisions themselves. For constraints, see CONSTRAINTS.md. For product definition, see ANCHOR.md.

---

## 1. The Superposition Principle

**Source:** Bayesian epistemology, quantum mechanics metaphor, formal belief revision (AGM theory, Dempster-Shafer)

A proposition doesn't have fixed meaning until it's retrieved with a specific intent. Before retrieval, it exists in a superposition of potential interpretations — "I'm drawn to teaching" could be evidence for a career pivot, a childhood pattern, a coping mechanism, or a core identity trait. The retrieval context collapses it into one interpretation. Different context, different collapse. Same data, different meaning every time.

This is not metaphor — it's a design principle. Meaning is not a property of knowledge. It's a property of retrieval context meeting a proposition. Tagging a proposition as "career" at write-time collapses its meaning prematurely. You've killed the cat.

Bayesian framing: confidence is conditional on retrieval context. "I'm drawn to teaching" might be high-confidence under an identity query and low-confidence under a career-action query. The system's confidence that its recorded model still matches the user's actual beliefs should decrease over time without refreshing evidence — not because the belief weakened, but because epistemic uncertainty grew. This reframes decay as a property of the system's knowledge, not the user's conviction.

Formal epistemology confirms: no model of belief revision (AGM, Bayesian, ranking theory, Dempster-Shafer) includes spontaneous time-based decay. Beliefs persist until evidence arrives. What decays is the system's warrant for claiming the model is still accurate.

**Voku connection:** Broad storage, narrow retrieval (ANCHOR.md Principle 3). Don't over-classify at ingestion (CONSTRAINTS.md #8). Meaning at read-time is the foundational architectural decision.

---

## 2. Motor Learning and the Constraints-Led Approach

**Source:** Bernstein's "repetition without repetition," ecological dynamics, PRI (Postural Restoration Institute), variational principle in physics

Bernstein showed that skilled movement isn't about memorizing solutions — it's about memorizing the shape of the problem space well enough to navigate it fresh each time. The system doesn't store motor programs; it develops sensitivity to constraints and generates contextually appropriate responses on the fly. Every execution is novel. The consistency is in the navigation, not the trajectory.

Ecological dynamics extends this: behavior self-organizes under constraints (organism, environment, task). You don't engineer the solution; you set the constraints and let the solution emerge. PRI adds that structural biases (left AIC, right BC patterns) create asymmetric constraint landscapes — the body doesn't explore the problem space uniformly.

The variational principle from physics: nature finds the path that minimizes action across the entire trajectory simultaneously — a global optimization, not a local one. The self you're becoming only makes sense across the whole trajectory, not at any single point.

**Voku connection:** Constraints-led extraction — the extraction paradigm shifted from entity-level to conversation-level because the right constraints (full conversation context) let propositions self-organize more naturally. The phase space visualization is a direct implementation: points positioned by geometric properties, structure emerging from distribution rather than predefined edges. Voku tracking belief evolution computes something like the variational solution — meaning that only resolves across the full trajectory.

---

## 3. Ecological Perception and Affordances

**Source:** James Gibson's ecological psychology, affordance theory

Gibson argued that perception isn't about building internal representations of the world — it's about directly perceiving affordances (action possibilities) in the environment. You don't compute that a chair is sittable; you perceive the sit-ability. The affordance exists in the relationship between the organism and the environment, not in either alone.

Applied to memory: you don't retrieve a belief — you perceive an affordance. The right context makes certain memories grip-able that were previously invisible. This isn't retrieval failure when you can't find something — it's absence of affordance. The memory was always there; the context didn't make it perceptible.

**Voku connection:** Voku as affordance engine — structure stored knowledge so that when you enter a problem space, relevant beliefs become perceptible. Not searched for. Just there. The phase space visualization literalizes this: nodes brighten and become visually salient based on current context, not because you queried for them. The user watches affordances emerge in real time.

---

## 4. Neural Compositionality and the Task Belief Signal

**Source:** Bushman lab (Princeton), published in Nature. Prefrontal cortex recordings during compositional task learning in primates.

The brain builds reusable orthogonal modules — a color module, a shape module, a motor command module — that exist as stable subspaces in neural activity. These modules are genuinely reused across tasks: a classifier trained to decode color in one task works almost perfectly on a different task that also requires color processing. The brain doesn't rebuild circuits from scratch for every new problem.

Two routing mechanisms make composition work:

1. **Railroad switch (output routing):** The same sensory signal (e.g., "red") gets routed to different motor outputs depending on task context. Same cargo, different destination. Task context flips the junction.

2. **Gain control (input selection):** A task belief signal amplifies relevant modules and suppresses irrelevant ones. When the monkey realizes it's in the color task, the color subspace stretches (red and green clouds separate) while the shape subspace compresses flat. Only the relevant information is loud enough to enter the routing switchboard.

The task belief signal is particularly striking — researchers could watch the monkey's realization unfold in real time as the belief signal physically reconfigured the neural geometry.

**Voku connection:** Propositions are the reusable modules — same knowledge components activated differently by different task contexts. Context assembly is the gain control mechanism — it amplifies relevant propositions and suppresses irrelevant ones based on the current query intent. The "same data, different projection, different structure" principle from ANCHOR.md is the computational analog of neural task-context-dependent routing. The phase space visualization is a direct externalization of what the prefrontal cortex does internally: reconfigure the geometry of knowledge based on what you're trying to do right now.

---

## 5. Compression as the Central Problem

**Source:** Borges ("Funes the Memorious"), information theory, survey of AI subdomain compression strategies

Borges imagined a man who remembered everything — every leaf, every moment, every sensation — and was paralyzed by it. Perfect memory is not intelligence. The compression function is the intelligence.

No AI subdomain has solved compression that is simultaneously goal-sensitive, context-aware, and able to update gracefully as goals change:

- LLMs: implicit compression in weights, invisible loss, can't audit
- RAG: no compression at all, navigation collapses at scale
- RL: reward-guided compression, brittle outside distribution
- Neurosymbolic: symbolic compression, loses contextual gradation
- Knowledge graphs: format predetermines representable relationships

**Voku connection:** Extraction IS the compression function — converting raw conversation into atomic propositions is a lossy compression that preserves what matters and discards what doesn't. The quality of this compression determines everything downstream. The unsolved challenge: making this compression goal-sensitive (what matters depends on what you're trying to do) and updatable (what matters changes as you change). Intent-triggered recall — matching current intent to stored intent, not just semantic similarity — is one approach to goal-sensitive compression.

---

## 6. Self-Referential Loops and the Observer Effect

**Source:** Second-order cybernetics (von Foerster), Bateson's ecology of mind, Hofstadter's strange loops, Goodhart's Law, Self-Determination Theory (Deci & Ryan)

Voku cannot be a passive observer of the user's beliefs. By showing users their belief patterns, the system creates a strange loop: the user's beliefs feed the model, the model feeds back to the user, the user's beliefs change in response, and those changed beliefs feed back into the model. Von Foerster's eigenform theory predicts that what Voku calls "a belief" is not something it discovers — it's a stable pattern that emerges from this recursive interaction. The tracked beliefs are co-constructed artifacts of the user-system loop.

Goodhart's Law: "Any observed statistical regularity will tend to collapse once pressure is placed upon it for control purposes." If Voku shows "your confidence in X is declining," the measurement becomes a target. The user may perform belief-consistency to avoid the metric, corrupting the signal.

Self-Determination Theory draws the critical line: when external tracking exerts controlling pressure, it undermines intrinsic motivation. When it serves an informational function, it enhances it. "Your commitment to X is declining" is controlling. "You've been thinking about X more this month" is informational.

Bateson's levels of learning: tracking individual belief changes is Learning I. Tracking patterns of change is Learning II — where character forms. Presenting Learning II observations to users can trigger Learning III processes (identity restructuring) that Bateson warned is dangerous territory.

**Voku connection:** The system doesn't discover who the user is. It co-creates a useful model of who they're becoming. This requires feedback damping (gain limiting, temporal smoothing, circuit breakers), shadow models the user doesn't see, and framing that is informational rather than controlling. The half-life decay mechanism naturally sorts eigenforms from artifacts: beliefs refreshed by genuine evidence survive; observation-dependent artifacts fade.

---

## 7. LLMs Get Lost in Multi-Turn Conversation

**Source:** Laban et al. (2025), "LLMs Get Lost in Multi-Turn Conversation." Microsoft Research + Salesforce. 200,000+ simulated conversations across 15 LLMs and 6 tasks.

All tested LLMs show a 39% average performance drop in multi-turn underspecified conversations versus single-turn. The degradation decomposes into a minor loss in aptitude (-15%) and a massive increase in unreliability (+112%). Even two-turn conversations trigger the effect. Lowering temperature doesn't help. Reasoning models (o3, DeepSeek-R1) don't help. The effect is universal.

Four root causes identified:

1. **Premature answer attempts:** LLMs generate full solutions before having enough information, planting incorrect assumptions that become fixtures.
2. **Answer bloat:** Subsequent attempts build on previous incorrect attempts rather than starting fresh, producing progressively longer and more assumption-laden responses.
3. **Loss of middle turns:** LLMs over-attend to the first and last turns of conversation, forgetting information from middle turns (analogous to "lost in the middle" for long-context).
4. **Over-verbosity:** Longer responses contain more assumptions, which compound across turns.

Agent-like interventions (RECAP: restating all info at the end; SNOWBALL: restating all info each turn) recover only 15-20% of the degradation. The paper concludes that LLMs should natively support multi-turn interaction, not rely on orchestration frameworks.

**Voku connection:** Voku's context assembly is a more sophisticated version of the SNOWBALL intervention — instead of naively repeating everything, it selectively retrieves relevant propositions and injects them as structured context. Proposition extraction is structurally anti-bloat: it strips verbose responses down to atomic claims. When served as context in future conversations, the model gets clean distilled knowledge rather than bloated conversation history. The paper's recommendation ("consolidate before retrying") is what Voku automates. The phase space makes context assembly visible — the user can see exactly which past propositions Claude is reading, addressing the loss-of-middle-turns problem by making retrieval auditable.

---

## 8. Context Engineering

**Source:** Dex Horthy's "12 Factor Agents" (2025), Karpathy's CPU/RAM framing (2025), Harrison Chase / LangChain, Anthropic context engineering guide (2025), Mei et al. academic survey (2025)

Karpathy's framing: LLMs are like a CPU, and the context window is like RAM. Context engineering is the operating system that manages what gets loaded into that RAM. The most important engineering work isn't writing prompts — it's building systems that dynamically assemble the right context for each LLM call.

Four core patterns (LangChain): Write (save context outside the window), Select (pull relevant context in), Compress (reduce tokens while preserving information), Isolate (separate context types).

Context rot: LLM performance degrades as context windows accumulate noise, contradictions, and outdated information. Research from Chroma showed that at 32K tokens, 11 of 12 tested models dropped below 50% of their short-context performance. The "dumb zone" kicks in when more than 40% of the context window is consumed.

**Voku connection:** Voku is a context engineering system by definition. It implements all four LangChain patterns: Write (extraction stores propositions outside the conversation), Select (retrieval pulls relevant propositions), Compress (propositions are compressed representations of full conversations), Isolate (system prompt context is separated from conversation history). The temporal dimension directly addresses context rot — knowing when a belief was current versus outdated prevents stale information from polluting the context window.

---

## 9. Secure Agent Architecture

**Source:** IBM + Anthropic, "Architecting Secure Enterprise AI Agents with MCP" (2025)

The paradigm shift from deterministic to probabilistic systems requires evaluation-first thinking — measurement of outcomes over implementation details. Key principles: least privilege (agents access only what they need), sandboxing (contain agent operations), audit trails (traceable decision chains), nonhuman identity management (agents get unique credentials), and human-in-the-loop oversight.

The threat model for agents includes: expanded attack surface, excessive agency, privilege escalation, data leakage, prompt injection, compliance drift, and agents as attack amplifiers due to autonomous operation.

**Voku connection:** Voku's architecture naturally implements several security principles. The LLM has read-only access to the proposition graph — it receives context but cannot write to it. Extraction is a separate, controlled pipeline with its own validation. The conversation → extraction → proposition → embedding chain is an auditable trace. Each proposition has provenance metadata (source conversation, timestamp, extraction confidence). The system prompt is assembled dynamically but from a constrained source (the proposition DB), not from arbitrary user input. For enterprise or portfolio framing: Voku demonstrates secure-by-design agent architecture where the AI's knowledge source is structured, auditable, and separated from its operational context.

---

## Threads Not Yet Developed

These connections have been noted but not fully explored:

- **Intent hierarchy** (immediate → domain → identity → psychological) as the organizing structure for proposition retrieval
- **Polar embedding visualization** — radius as generality (modules near origin, leaves at periphery), connecting containment hierarchy to visual structure
- **Node hierarchy** (leaf → internal → module) as analog to neural subspace hierarchy
- **Spaced repetition vs. narrative learning** — why narrative (intent as container) produces better retention than isolated fact repetition, and implications for how Voku surfaces information
- **Attractor dynamics and phase transitions** in belief change — when smooth derivative models break down and bistable switching takes over
