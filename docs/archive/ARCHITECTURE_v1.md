# Voku Architecture
**Created:** 2026-02-15
**Status:** Authoritative build plan. Replaces COMPONENT_SPEC.md for strategic direction.
**Last Updated:** 2026-02-15T19:30

> "The system doesn't discover who the user is. It co-creates a useful model of who they're becoming."

---

## 1. Purpose

Voku is a cognitive mirror — an observation engine that externalizes how a person allocates attention, time, and energy, and reflects that model back so they can see what they actually prioritize, how their understanding evolves, and where their stated intentions diverge from their revealed behavior.

The fundamental substrate is **time and energy allocation.** Everything a person does — training, scrolling, building, conversing, sitting in afternoon murk — is a use of finite resources. Beliefs emerge from these allocations. Intentions predict them. Events record them. The gap between what someone says they'll do and what they actually do is the most diagnostic signal about who they actually are.

**The practice of interacting with Voku is itself the intervention.** The user develops a habit of externalizing, inspecting, and curating their own cognitive context. Voku doesn't just observe the user — it inserts a feedback checkpoint into a naturally circular process (context → task selection → context) that previously had no external visibility. The mirror changes what it reflects by the act of reflecting it.

### What Voku Is Not
- Not a retrieval system (retrieval is infrastructure, not purpose)
- Not an AI advisor (doesn't generate ideas or recommendations)
- Not a productivity tool (surfaces self-knowledge that makes productivity *possible*)
- Not a passive observer (it's a participant in a self-referential feedback loop)

### The Problem It Addresses
1. **Lossy self-compression** — nuanced evaluations flatten into harsh verdicts through repeated recall
2. **Invisible context pollution** — physical/emotional states silently degrade cognition without awareness
3. **The articulation paradox** — tools that require self-knowledge to configure are useless to those who lack it

### The Landscape Gap
Every system in the AI memory landscape (Mem0, Graphiti, LangMem, Letta) points output at the AI. Voku points output at the human. The AI is the mirror's surface. The human is the one looking into it. No existing system tracks belief evolution — the temporal dimension of personal knowledge is essentially unstudied in production systems.

---

## 2. Version Roadmap

### v0 — Thesis Proof (Current → Demo)
**Question:** Does temporal tracking produce meaningfully better retrieval than flat memory?
- Ingest real conversations, extract propositions, detect belief evolution
- Evaluate: temporal retrieval accuracy vs flat baseline
- Deliverable: working prototype + metrics proving the thesis
- Scope: explicitly stated beliefs only, single user, batch processing

### v1 — Observation Engine (Post-Demo)
**Question:** Can Voku reliably observe stance evolution, behavioral patterns, and intention-event gaps?
- Clean extraction pipeline: 3 node types + cognitive operations + conversation metadata
- Basic synthesis layer: pattern/gap/trajectory generation
- User confirmation loop: Voku proposes → user validates → confirmed = durable knowledge
- Power-law confidence decay (system confidence about model accuracy, not belief strength)
- Entrenchment ranks parameterizing decay rates
- MCP integration serving live context to Claude Desktop

### v2 — Intelligence Layer (Research Phase)
**Question:** Can Voku detect the *structure* of belief change — networks, transitions, coupling?
- Belief network graph: connectivity influences behavior (connected beliefs persist, isolated ones decay)
- Node hierarchy: leaf → internal → module (hierarchical search)
- Task-contextual retrieval: same graph reorganizes based on what user is doing
- Bayesian state estimation replacing point confidence scores
- Transition detection: variance monitoring for pre-shift signals (critical slowing down)
- Cross-derivatives: stance-event coupling, intention-event conversion rates

### v3 — Mirror (Product Vision)
**Question:** Can Voku manage its own feedback effects responsibly?
- Debuggable interface: user sees Voku's inferences, corrects them, corrections become data
- Feedback loop management: circuit breakers, gain limiting, shadow model
- Observer derivative: measuring Voku's own impact on user behavior
- Multi-source ingestion: calendar, health metrics, screen time alongside conversation data
- Polar/3D visualization: radius = generality, angle = domain
- Multi-user architecture (if productized)

### What Each Version Proves
| Version | Proves | Audience |
|---------|--------|----------|
| v0 | Temporal > flat retrieval (with numbers) | Hiring managers, portfolio reviewers |
| v1 | Observation engine works on real ongoing data | Jaymin as daily user, blog readers |
| v2 | Network structure reveals things derivatives can't | Research community, thesis reviewers |
| v3 | Self-referential feedback can be managed | Product users, the field |

---

## 3. Three Capabilities

These are Voku's functional outputs. Everything in the architecture serves one or more of these.

### 3.1 Stance Tracking
Beliefs evolve via supersession. "Ankle is my rowing limiter" → "Breathing is my rowing limiter."
- **Input:** Stance propositions with timestamps
- **Processing:** Detect contradiction/supersession between stances via semantic similarity + LLM classification
- **Output:** Belief timelines, supersession edges, status updates (active → superseded)
- **Key insight (from cross-domain research):** High-involvement belief changes are discrete phase transitions (cusp catastrophe), not smooth derivatives. The SUPERSEDES edge already handles this correctly — belief change is modeled as event-driven, not time-driven.

### 3.2 Behavioral Pattern Detection
Events accumulate; patterns emerge from frequency and correlation.
- **Input:** Event propositions (behavioral observations, actions taken)
- **Processing:** Frequency analysis, clustering, correlation detection across events
- **Output:** Pattern synthesis nodes ("scrolls after lunch on weekdays")
- **Lineage:** Billy's awareness layer (Dec 14-22, 2025), feature extraction on 3,768 messages. Dropped during Jan 22 descoping, now returning with proper architecture.
- **Key constraint (from signal detection research):** Need 30-50 observations minimum for reliable pattern detection. Weekly behaviors need 2-3 months of data. Surface patterns with explicit confidence intervals, not point claims.

### 3.3 Stated-vs-Revealed Gap Detection
Intentions compared against events.
- **Input:** Intention propositions + subsequent event propositions
- **Processing:** Match intentions to fulfillment events; detect unfulfilled, abandoned, or persistent intentions
- **Output:** Gap synthesis nodes ("said would work on Voku, no Voku event logged")
- **Lineage:** "Billy is the derivative of productivity planning" (Jan 30 concept file). Goals aren't the anchor. Self-understanding is the anchor. Goals are a byproduct.
- **Key insight:** This doesn't need derivatives or half-lives. It needs binary matching (did the event happen?) with sophistication in aggregation (conversion rate over time).

---

## 4. Data Model

### 4.1 Three Node Types (Processing Semantics)

Every extracted proposition is exactly one of:

| Type | Definition | Processing Pipeline | Examples |
|------|-----------|---------------------|----------|
| **Stance** | Position that can be superseded | Supersession detection, contradiction detection, confidence evolution | "Breathing is my rowing limiter", "I think concurrent training is better", "Voku should use SQLite" |
| **Event** | Thing that happened | Accumulation, frequency analysis, correlation, clustering | "Scrolled after lunch", "Had E1 Row session", "Felt afternoon murk", "Skipped training" |

**Event timeframe dimension:**
| Timeframe | Definition | Examples |
|-----------|-----------|----------|
| `recent` | Within the conversation period (weeks/months) | "Scrolled after lunch", "Had E1 Row session" |
| `historical` | Before the conversation period | "Went to 9 schools K-12", "Studied motor learning at Columbia" |
| `ongoing` | Recurring or persistent state/fact | "Father is CEO of Korean investment bank", "Lives in Vancouver" |
| **Intention** | Declared commitment | Fulfillment tracking (paired against events), abandonment detection | "I want to work on Voku tomorrow", "Goal: 2K row time under 8:00", "Will start nutrition protocol" |

**Stories are compound propositions.** Natural speech bundles types together. "I went to 9 schools and that instability created my hypervigilant self-evaluation" contains an immutable historical event (9 schools) and a supersedable interpretive stance (instability → hypervigilance). The extraction layer decomposes stories into their atomic types, linked by shared provenance. This decomposition is what makes derivatives computable — the event is the integral (accumulated history), the stance is the derivative (current interpretation applied to that history). The same event can produce different interpretive stances over time; Voku sees the change because it stored them separately.

**"Ongoing" events blur toward stances** — and that's resolved by processing semantics. "I have an interest-based nervous system" looks like a fact but functions as an identity-level stance (supersedable if understanding changes). Classify by pipeline: accumulates → event, supersedes → stance.

**Why three, not seven:** Original types (BELIEF/GOAL/OBSERVATION/DECISION/PATTERN/LEARNING/EMOTIONAL) collapsed because processing semantics are what matter, not content description. A DECISION is a stance (it supersedes the previous approach). A GOAL is an intention (it gets fulfilled or abandoned). An EMOTIONAL observation is an event (it accumulates for pattern detection). Type = which pipeline processes it.

### 4.2 Confidence Model

**Critical reframe from cross-domain research:** Confidence represents **system certainty that its model matches reality**, not belief strength. Without new evidence, system certainty should decrease — not because the user's belief is weakening, but because Voku can't know whether it's still current.

**Power-law decay** (not exponential):
```
system_confidence = base_confidence × (t_since_last_evidence + 1) ^ (-β)
```
Power-law gives a long tail — old beliefs retain faint residual rather than vanishing. Matches human memory: you don't forget your old training philosophy, it's just less accessible until triggered.

**Decay rate parameterized by entrenchment rank:**
| Rank | Examples | Approximate Half-Life | β |
|------|----------|----------------------|---|
| Identity/value | "I build tools to help humans see themselves" | Months–years | ~0.1 |
| Approach/method | "Concurrent training is better than sequential" | Weeks–months | ~0.3 |
| Preference/taste | "I prefer SQLite over Postgres for this" | Days–weeks | ~0.5 |
| Situational | "I'm feeling tired today", "Plan for tomorrow" | Hours–days | ~1.0 |
| Intention | Deadline-governed, not time-decayed | Special: decays on deadline miss, not by time | N/A |

**v0 implementation:** base_confidence from LLM extraction, no decay computation. Decay is a v1 feature.

### 4.3 Synthesis Nodes (Voku-Generated)

Three types, all user-confirmable:

| Type | Source | Example |
|------|--------|---------|
| **Pattern** | Event accumulation | "You scroll after lunch on weekdays" |
| **Gap** | Intention-event comparison | "Said would do Voku, didn't — 3 of 5 times this month" |
| **Trajectory** | Stance evolution chain | "Training philosophy shifted from performance-first to consistency-first over 6 weeks" |

**Lifecycle:** Generated by processing pipeline → surfaced to user → user confirms or rejects → confirmed = durable knowledge, rejected = training signal. This is the Dec 18 "unsupervised → validate → encode" loop.

**v0 implementation:** No synthesis nodes. v1 feature.

### 4.4 Node Hierarchy (v2)

| Level | Description | Example |
|-------|------------|---------|
| Leaf | Atomic propositions (extraction output) | "Breathing limits my rowing catch" |
| Internal | Confirmed abstractions (user-validated clusters) | "Training philosophy evolution" |
| Module | Domains | Training, Career, Psychology, Voku |

Enables hierarchical retrieval: identify relevant module → search within subtree. Solves flat embedding search's "everything is related" problem.

**v0 implementation:** Flat propositions only. Hierarchy is v2.

---

## 5. Extraction Model

### 5.1 Two-Pass Architecture (v1+)

**Pass 1 — Conversation Level:** Read full conversation, tag metadata.
- opening_mode: exploring / executing / processing / venting
- trajectory: deepened / pivoted / resolved / abandoned
- closing_state: energized / depleted / uncertain / decided

**Pass 2 — Message Level:** Extract propositions from user messages only.
- AI messages used as comprehension context, never as proposition sources
- Each proposition gets: text, node_type, cognitive_operation, confidence

**v0 implementation:** Single-pass extraction with node_type classification. Conversation metadata and cognitive operations are v1 features.

### 5.2 Cognitive Operations (v1+)

What the user is *doing* cognitively with a statement:

| Operation | Description | Confidence Effect |
|-----------|-------------|-------------------|
| Exploring | Testing an idea, first mention | Lower confidence |
| Declaring | Committing to a position after reasoning | Higher confidence |
| Reporting | Describing what happened | High confidence (factual) |
| Processing | Working through emotions/confusion | Context-dependent |
| Evaluating | Assessing something against criteria | Medium confidence |
| Planning | Stating future actions | Intention-type, deadline-governed |

Same words = different operations. "I think concurrent training is better" as exploration (first mention) vs declaration (after 45 minutes of reasoning) = different confidence, different processing.

**v0 implementation:** Not extracted. v1 feature requiring extraction prompt redesign.

### 5.3 Story Decomposition Principle

When the user tells a story about their past, the extraction prompt must separate:
1. **The factual event** — what happened (immutable, gets `event` type + `historical` timeframe)
2. **The interpretive stance** — what the user believes it means *now* (supersedable, gets `stance` type)

Both propositions share provenance (same message, same conversation). This decomposition is required because the event won't change but the interpretation will — and tracking that divergence over time is Voku's core value.

Example: "I went to 9 schools K-12, which is why I have this hypervigilant internal monitor" →
- Event (historical): "Attended 9 schools during K-12"
- Stance (identity): "K-12 school instability is the source of hypervigilant self-evaluation pattern"

### 5.4 Opening Message as Behavioral Telemetry (v1)

The first message in every conversation is a voluntary state snapshot: time, location, recent events, current intention. Closest to uncontaminated measurement — user hasn't been shaped by AI responses yet.

Extract separately as structured `opening_snapshot` with fields: `{time, location, recent_event, stated_intention, inferred_state}`. Seeds session context metadata for extraction prompt. Over 60+ conversations, accumulates into a structured behavioral dataset for pattern detection.

**Selection bias:** Opening messages sample from activated states only. Mundane middle doesn't generate conversations. Good for "what triggers sessions" — poor for broad behavioral patterns. Full behavioral data requires external sources (v3).

**v0 implementation:** Not extracted separately. v1 feature.

### 5.5 Source Filtering Rules

- **Extract from:** User messages only
- **Use as context:** AI messages (for comprehension, not proposition extraction)
- **Strip:** Thinking blocks, tool calls, base64 images, footer lines
- **Preserve:** Provenance fields (source_char_start/end, source_file, session_id, message_index)

### 5.6 User Declarations (Direct Input Channel)

Not all input should pass through conversation extraction. A declarations file provides a direct, unmediated channel for the user to seed or correct Voku’s model. This solves three problems:

1. **Cold start.** Voku can begin with user-declared stances, events, and intentions before any conversation is ingested. No extraction error, no AI bias.
2. **Eigenform escape.** Conversation-extracted propositions are beliefs-as-expressed-through-an-AI-interlocutor. Declarations bypass that loop — the user states what they believe without scaffolding shaping the expression.
3. **Correction as data.** When the user edits or deletes an extracted proposition, that correction is itself a temporal event — a user-confirmed supersession with the highest provenance quality.

**v0 format:** YAML file, manually edited, ingested through the same pipeline as conversation extractions.

```yaml
# voku_declarations.yaml
- text: "Concurrent training is better than sequential for my goals"
  type: stance
  entrenchment: approach
  declared: 2026-02-15

- text: "Attended 9 schools K-12"
  type: event
  timeframe: historical

- text: "Start LeetCode practice by May 2026"
  type: intention
  deadline: 2026-05-01
```

Declarations get `source_type: "user_declared"` and higher base confidence than conversation-extracted propositions (no extraction error margin). They use the same storage, embeddings, and retrieval as all other propositions.

**v0 Phase 4:** Replace the YAML file with a proposition viewer/editor UI (React app). See what Voku extracted, correct it, add new declarations, delete noise. The feedback loop between extraction and user correction is the product.

**Evaluation dimension:** The ablation study gains a third axis — extracted vs. declared vs. both. If declared propositions retrieve better (expected: cleaner signal), that’s a baseline. If extracted propositions add value on top (expected: capture what the user didn’t think to declare), that proves the extraction pipeline is worthwhile.

---

## 6. Processing Pipelines

One per node type. Each runs during the "process" phase after ingestion.

### 6.1 Stance Pipeline
```
New stance → find semantically similar existing stances (embedding search)
  → for each similar pair: LLM classifies relationship
    → SUPPORTS: create edge, optionally boost confidence
    → CONTRADICTS: create edge, flag for user review
    → SUPERSEDES: create edge, update older stance status to "superseded"
    → UNRELATED: skip
```

**Supersession provenance:** SUPERSEDES edges should carry `evidence_conversation_ids` — which conversations contributed to the belief change. Conversation-level extraction already co-extracts events, stances, and intentions with shared provenance. For v0 Phase 3: add the field, populate manually for golden set cases. For v1: automatic evidence linking via temporal proximity + semantic similarity of events to new stance.

**Entrenchment heuristic for resolution:** When both propositions have high entrenchment, surface to user rather than auto-resolving. When one has low entrenchment, auto-resolve. Simple heuristic that improves the pipeline without adding complexity.

**v0 implementation:** This IS the core of Milestone 3 (process engine). Spike S4 validates LLM classification accuracy before building.

### 6.2 Event Pipeline (v1+)
```
New event → accumulate in event store
  → periodic pattern detection:
    → frequency analysis per domain/topic
    → correlation detection (co-occurring events)
    → clustering (semantically similar events)
  → when pattern confidence exceeds threshold:
    → generate Pattern synthesis node
    → surface for user confirmation
```

**v0 implementation:** Events stored but not processed for patterns. Pattern detection is v1.

### 6.3 Intention Pipeline (v1+)
```
New intention → track against subsequent events
  → if matching event found within window: mark fulfilled
  → if deadline passes without event: mark unfulfilled
  → if intention restated without fulfillment: increment persistence count
  → when gap pattern emerges (repeated unfulfillment in domain):
    → generate Gap synthesis node
    → surface for user confirmation
```

**v0 implementation:** Intentions stored but not tracked against events. Gap detection is v1.

### 6.4 Consolidation Scheduler — The "Exhale" (v1)

The breathing architecture: inhale is goal-agnostic (extract and store everything faithfully). Exhale is multi-goal (consolidate through recently-active lenses).

The consolidation scheduler runs periodically and replays accumulated propositions through N most recently active goal contexts (derived from session metadata across recent conversations, weighted by recency and frequency). For each proposition in the consolidation window:

1. Compute activation against each goal context (embedding similarity + connection to other activated propositions)
2. Propositions exceeding threshold in 3+ contexts → entrenchment boost (empirically cross-domain)
3. Single-context activation → current entrenchment maintained
4. Zero-context activation → power-law decay applied

This discovers entrenchment from data rather than requiring manual assignment. "I build tools to help humans see themselves" activates in career, Voku, self-analysis, and relationship contexts → empirically identity-level. "I prefer SQLite over Postgres" activates only in Voku context → empirically preference-level.

Candidate internal nodes emerge from propositions that consistently co-activate across contexts. System suggests clusters; user names, confirms, adjusts boundaries. Collaborative taxonomy, not automatic abstraction.

**Key principle:** Storage is goal-agnostic (ADR_002). Consolidation is multi-goal. The intelligence is in the evaluation, not the filtering. Nothing gets dropped — propositions get scored.

**v0 implementation:** No consolidation. v1 feature requiring enough accumulated data and distinct goal contexts.

---

## 7. Retrieval Model

### 7.1 Three Modes

| Mode | Description | Version |
|------|------------|---------|
| **Flat** | Pure embedding similarity (baseline) | v0 |
| **Temporal** | Similarity + status awareness + recency weighting | v0 |
| **Task-contextual** | Weighted module activations per task context | v2 |

**Meaning computed at read-time** (ADR_002). Propositions are tokens; meaning is recomputed through attention to the query context, not stored as static labels.

### 7.2 The Circularity

The task determines which context is retrieved. But the accumulated context determines which tasks the user chooses. Retrieval and observation are the same system running in opposite directions:
- **Retrieval direction:** Given a task, activate relevant context
- **Observation direction:** Given accumulated context, surface what patterns/gaps emerge

This circularity is Voku's core value proposition, not a limitation. Every other system treats the user as static. Voku models a system in motion.

### 7.3 Evaluation (v0, Critical)

**Reframe (Feb 16):** The ablation tests **model accuracy over time**, not retrieval improvement. Retrieval is the measurement instrument. Voku isn't competing with RAG systems. It's demonstrating that temporal organization produces a more accurate representation of who someone is *right now*. Frame for portfolio: "temporal organization produces a more accurate model of evolving self-knowledge, demonstrated through retrieval accuracy as proxy metric."

**Ablation study:** Three-way comparison on golden test set.
1. No context (baseline)
2. Flat retrieval (embedding similarity only)
3. Temporal retrieval (similarity + status + recency)

**Key metric:** Temporal accuracy — % of queries where temporal retrieval returns the *current* correct belief vs flat retrieval returning an outdated one.

**Competitive positioning (from research report):** MemoryStress benchmark found only 21.4% accuracy on contradiction resolution across all systems tested. If Voku achieves even 50% on contradiction/supersession cases, it more than doubles the field's best.

**Go/no-go gate:** End-to-end temporal accuracy must exceed 70% on golden set temporal cases before proceeding to full build. Below 70% → narrow scope or simplify.

---

## 8. Interaction Model

### 8.1 CQRS Pattern
- **Reads:** Live during conversation (MCP server serves context to Claude Desktop)
- **Writes:** Three channels, in order of signal quality:
  1. **User declarations** (highest confidence) — direct YAML input or proposition editor. No extraction error. User explicitly states and classifies.
  2. **User corrections** (high confidence) — edits to extracted propositions via viewer/editor. Corrections are themselves temporal events (user-confirmed supersessions).
  3. **Conversation extraction** (standard confidence) — batched post-conversation pipeline. Subject to extraction error and AI-mediation bias. Earlier messages in conversation = higher confidence than later ones.

### 8.2 Proposition Viewer/Editor (v0 Phase 4)
User sees what Voku inferred: which cognitive operation, what evidence, what comparison. User can correct any of these. Corrections become data.

### 8.3 Privacy Architecture: User-Controlled Disclosure

Privacy is not binary (local vs cloud). The user determines how much to disclose from their Voku at every layer.

**Three privacy boundaries:**

| Layer | Default | User Control |
|-------|---------|-------------|
| Storage | Always local (SQLite file, user owns it) | Full ownership, portable, deletable |
| Extraction | Provider-agnostic (Ollama local or Groq/Claude cloud) | User chooses per-run. Cloud = faster/better. Local = nothing leaves device. |
| Retrieval/Serving | Local MCP server → cloud LLM (Claude Desktop) | Propositions served only if `shareable: true`. User reviews via viewer/editor before anything is shared. |

**Extraction provider options:**

| Privacy Level | Provider | Trade-off |
|---|---|---|
| Maximum | Ollama (local) | Slower, lower quality on small models. Nothing leaves the machine. |
| Balanced | Groq free tier | Fast, good quality. Data transits to Groq servers. |
| Convenience | Claude/OpenAI API | Best quality. Costs money. Data transits to provider. |

The user chooses their provider in config. Switching is a config change, not a code change (Constraint 3.13).

**The privacy gate is the proposition viewer/editor** (v0 Phase 4). The user reviews what Voku extracted and controls what enters the retrieval pool:
- Mark propositions as `shareable: false` (never served to external models via MCP)
- Delete propositions entirely
- Edit propositions before they enter the retrieval pool
- Choose extraction provider (local vs cloud) per batch

User corrections and redactions are themselves data — they reveal what the user considers private, which is self-knowledge.

**Provider defaults:**
- **Production default:** Ollama (local-first, per CONSTRAINTS.md Tier 3.11)
- **Development:** Groq (free, avoids Claude-on-Claude extraction bias)
- **v0 Phase 4:** User-facing privacy toggle in the proposition viewer/editor UI

Note: Using a non-Claude model (Groq/Ollama) for extraction of Claude conversations is arguably *better* for objectivity — the extraction LLM has no self-recognition of Claude-style outputs, reducing eigenform bias in the extraction layer.

### 8.4 Feedback Loop Awareness (v3)
Cross-domain research confirms: Voku's observations change what it observes. The eigenform framing: tracked beliefs are co-constructed artifacts of the user-system loop. Design implications:
- Gain limiting on reported metric changes
- Circuit breakers for positive feedback spirals
- Present information informationally, not controlling (SDT framework)
- Support "happy abandonment" — users who learned what they needed and moved on

---

## 9. v0 Build Sequence

Current state: Milestone 1 COMPLETE (29/29 tests). Golden set database EXISTS (332 propositions, contaminated with AI messages).

### Phase 1: Clean Foundation
1. **Temporal signal audit** — scan 21 fixtures for explicit belief evolution instances (stance A at time T₁ → stance B at time T₂). Need 3-5 cases to support thesis. Determines whether data supports the demo before building extraction around it.
2. **Re-extraction prompt design** — user messages only (AI messages as comprehension context), node_type (stance/event/intention), event_timeframe (recent/historical/ongoing), story decomposition (separate event from interpretive stance), supersedable fallback field, explicit beliefs only
3. **Spike S4b** — node type classification accuracy. Hand-label 20-30 propositions from existing 332 as ground truth. If <65% three-way accuracy but >80% binary supersedable accuracy, defer trichotomy to v1.
4. **Sample validation** — test new prompt on 3-5 conversations, evaluate classification accuracy. Include at least 1 story-heavy conversation to validate decomposition. Also test on 1 standalone text (vault concept file) to validate non-conversational extraction.
5. **Declarations file parser** — YAML ingestion path for user-declared propositions. Same pipeline (embed → store), `source_type: user_declared`, higher base confidence.
6. **Full re-extraction** — if sample validates, re-extract all 21 conversations with new prompt
7. **Spike S4** — LLM relationship classification reliability on 10 known-ground-truth pairs

### Phase 2: Prove Retrieval
5. **Hand-craft 10-15 golden set queries** — temporal cases, basic retrieval, contradiction cases
6. **RetrievalService** — flat + temporal modes
7. **EvaluationHarness** — run golden set, compute metrics, first ablation

### Phase 3: Prove Temporal Tracking
8. **ProcessEngine** — stance pipeline only (detect supersession/contradiction)
9. **Re-run evaluation** — temporal accuracy delta vs flat baseline
10. **Gate test** — "What is the user's rowing limiter?" returns breathing, not ankle

### Phase 4: Make It Usable
11. **MCP server** — serve temporal context to Claude Desktop
12. **Proposition viewer/editor** — React app (agentic-coded, 4-6 hours). Table or card view of all propositions. Filter by node_type, status, timeframe. Inline edit, add new declarations, delete noise. This is the v3 debuggable interface pulled forward to minimum viable scope — the user sees what Voku extracted and corrects it. Corrections are user-confirmed supersessions (highest-quality temporal data).
13. **If time: timeline view** — chronological view of events and stance evolution. Calendar-style for events/intentions, chain view for stance supersession.

### Schema Additions for v0
Beyond existing tables (propositions, embeddings, edges, thread_surfaces):
- Add `node_type` to propositions (stance/event/intention) — replaces current generic type
- Add `event_timeframe` to propositions (recent/historical/ongoing) — populated for event-type nodes only
- Add `entrenchment_rank` to propositions (identity/approach/preference/situational) — manually populated for golden set
- Extend `source_type` enum: conversation | user_declared | standalone_text
- Add `message_position` to propositions (integer) — position within conversation, confidence signal (earlier = less AI-mediated)
- Add `shareable` to propositions (boolean, default true) — privacy gate for MCP serving. User sets via viewer/editor.
- Add `evidence_conversation_ids` to edges table (JSON array) — which conversations contributed to belief change. Populated manually for golden set in Phase 3, automatic linking in v1.

### Schema Reserved for v1+ (create tables but don't populate)
- `abstractions` — internal nodes (leaf → internal → module hierarchy)
- `contains_edges` — hierarchy relationships
- `synthesis_nodes` — Voku-generated patterns/gaps/trajectories
- `conversation_metadata` — opening_mode, trajectory, closing_state per conversation
- `opening_snapshots` — structured state from first message: time, location, recent_event, stated_intention, inferred_state
- `session_contexts` — goal contexts active per session, weighted by recency/frequency. Used by consolidation scheduler.
- `consolidation_runs` — log of exhale cycles: which propositions evaluated, which contexts used, entrenchment changes applied

---

## 10. Research Foundations

### Cross-Domain Findings (Feb 15 analysis)

Seven domains researched: signal detection theory, dynamical systems (cusp catastrophe), formal epistemology (AGM, Bayesian, Dempster-Shafer), truth maintenance systems, second-order cybernetics (von Foerster, Bateson), self-determination theory, and lived informatics.

**Incorporated into architecture:**
- Power-law confidence decay (not exponential) — beliefs retain faint residual
- Confidence = system certainty about model accuracy, not belief strength
- Entrenchment ranks parameterizing decay rates
- Discrete supersession events (not smooth derivatives) for high-involvement beliefs
- Sparse data caution: 30-50 observations needed for reliable pattern detection
- Eigenform framing: Voku co-creates a model, doesn't passively discover one

**Deferred to v2+:**
- Bayesian state estimation (posterior distributions instead of point scores)
- Belief network connectivity influencing decay behavior
- Transition detection via variance monitoring (critical slowing down)
- Feedback loop damping mechanisms (circuit breakers, shadow model)
- Three-valued belief model: aspirational/operational/acknowledged_tension (requires behavioral pattern detection first)

**Incorporated from Feb 16 deep research report:**
- Behavioral inference framing: "revealed operational priorities" not "implicit beliefs" (Youyou et al. PNAS: 10 Likes outperform colleague, 300 outperform spouse)
- Self-report vs behavioral measures correlate r=0.00 to 0.20 (Dang, King, Inzlicht 2020) — validates conversation extraction as limited signal, not ground truth
- Measurement reactivity: completing questionnaires increased physical activity 20 min/day (French & Sutton) — citable evidence for "interaction is the intervention"
- MemoryStress benchmark: 21.4% contradiction resolution across all systems — Voku's competitive positioning
- ACT-R activation function: `Activation = Base-level + Spreading + Noise` with power-law base-level — aligns with existing decay model, adds spreading activation for v1
- LongMemEval: round-level storage optimal granularity — validates conversation-level extraction (1,758 → 144)
- Entrenchment heuristic for contradiction resolution: auto-resolve low-entrenchment, surface high-entrenchment to user
- Go-CLS selective consolidation: only memories aiding generalization should consolidate — informs v1 consolidation scheduler design

**Already present in architecture:**
- Justification chains (provenance fields since v0)
- Belief network graph (edges table)
- User-confirmable synthesis (Dec 18 validate → encode loop)
- Episodic engagement model (batch import)
- Separated inference/display (CQRS)

### Development Arc
| Phase | Period | Key Contribution |
|-------|--------|-----------------|
| Billy OS | Dec 14-22, 2025 | Mirror + reasoning layers, unsupervised → validate → encode loop, awareness layer, multi-agent architecture |
| Billy Features 1-10 | Dec 22 - Jan 8, 2026 | Calendar/scheduling, somatic check-ins, plan generation. Proved: operational data alone isn't enough |
| Billy → Voku Pivot | Jan 22, 2026 | Descoped from multi-agent OS to knowledge graph. "Temporal belief tracking" became the thesis |
| Personal Context Thesis | Jan 26, 2026 | Multi-domain context architecture, personal API vision |
| Derivative Concept | Jan 30, 2026 | "Billy is the derivative of productivity planning" — stated vs revealed gap as core value |
| Architecture Migration | Feb 10-11, 2026 | Kuzu → SQLite, meaning-at-read-time (ADR_002), spec-driven development |
| Build Sprint | Feb 13-14, 2026 | M1 complete (29/29), golden set database (332 propositions) |
| Observation Engine | Feb 15, 2026 | Node types 7→3, cognitive operations layer, AI message contamination discovered, Billy feature resurrection |
| Cross-Domain Research | Feb 15, 2026 | Seven-domain analysis validates architecture, adds power-law decay, eigenform framing |
| Breathing Architecture | Feb 16, 2026 | Goal-agnostic storage + multi-goal consolidation. Opening messages as telemetry. Supersession provenance. Ablation = model accuracy. Eigenform → collaborative taxonomy. Advisory model rejected. |

---

## 11. Key Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| Privacy = user-controlled disclosure | Not binary local/cloud. Three boundaries (storage/extraction/serving). Proposition viewer/editor is the privacy gate. `shareable` flag on propositions. Groq for dev (avoids Claude-on-Claude bias). | Feb 15 |
| User declarations as v0 data source | YAML file for direct, unmediated user input. Solves cold start, eigenform escape, and correction-as-data. Higher base confidence than extracted propositions. | Feb 15 |
| Proposition viewer/editor in v0 Phase 4 | v3 debuggable interface pulled forward to MVP scope. Agentic-coded React app. User corrections = highest-quality temporal data. | Feb 15 |
| Story decomposition principle | Stories are compound: event (integral) + interpretive stance (derivative). Decompose at extraction, link via provenance. Enables tracking reinterpretation over time. | Feb 15 |
| Event timeframe dimension | recent/historical/ongoing — events have temporal context beyond conversation timestamp | Feb 15 |
| Observation engine identity | Three capabilities: stance tracking, pattern detection, stated-vs-revealed gap | Feb 15 |
| Node types 7→3 | stance/event/intention map to distinct processing pipelines | Feb 15 |
| Extract user messages only | AI messages = scaffolding for user thinking, not user knowledge | Feb 15 |
| Power-law decay | Beliefs retain faint residual; exponential decay incorrectly zeroes out old beliefs | Feb 15 |
| Confidence = system certainty | Not belief strength. Absence of evidence increases uncertainty about model accuracy | Feb 15 |
| Architecture document before implementation | Top-down validation prevents analyzing what exists before questioning whether it's correct | Feb 15 |
| Demo timeline flexible | "Build the right thing" > hitting March 31. Thesis quality > schedule adherence | Feb 15 |
| Breathing architecture: goal-agnostic storage, multi-goal consolidation | Inhale stores everything (ADR_002). Exhale evaluates through N recent goal contexts. Intelligence in evaluation, not filtering. | Feb 16 |
| Multi-context consolidation discovers entrenchment | Cross-context activation replaces manual entrenchment assignment. 3+ contexts = identity-level. 1 context = preference-level. | Feb 16 |
| Supersession provenance | SUPERSEDES edges carry evidence_conversation_ids. Preserve WHY beliefs changed. v0: manual for golden set. v1: automatic. | Feb 16 |
| Opening messages as behavioral telemetry | First message = voluntary state snapshot. Extract as structured opening_snapshot. Bridges to structured data (v3). Selection bias: activated states only. | Feb 16 |
| Ablation framed as model accuracy, not retrieval | Retrieval is measurement instrument. Selling point: temporal org → accurate model of evolving self-knowledge. | Feb 16 |
| MEM1-style write buffer rejected | Reintroduces goal-relative abstraction loss at storage time. Keep storage goal-agnostic per ADR_002. | Feb 16 |
| Advisory model rejected | Mirror, not advisor. Curation through revelation, not recommendation. | Feb 16 |
| Module nodes = collaborative taxonomy | System suggests clusters from co-activation. User names, confirms, adjusts. Not automatic abstraction. | Feb 16 |
| SQLite + numpy architecture | Single file, no external services, portable. Minimum viable complexity | Feb 11 |
| Spec-driven development | CONSTRAINTS.md + specs. Tests before implementation | Feb 11 |
| bge-base over EmbeddingGemma | Spike S2: bge-base wins on retrieval quality, no Ollama dependency | Feb 13 |

---

## 12. Risks (Updated)

### Active (affect v0)
- **R1: Extraction accuracy compounds.** End-to-end temporal accuracy = extraction × classification. If extraction or S4 fail, narrow scope.
- **R1b: Node type classification accuracy.** Can the LLM reliably distinguish stance/event/intention? Unknown. Test before building pipelines around it.
- **R3: Evaluation might show thesis doesn't work.** Honest results are still portfolio-worthy. "I measured rigorously and found X" is a strong story.

### Deferred
- **R2: Platform window.** 12-18 months before platforms attempt belief tracking. Ship blog post by April.
- **R4-R7:** Retention, psychological resistance, market size, tools-for-thought graveyard. See `voku — risk assessment.md`.

---

## File References

| File | Purpose | Status |
|------|---------|--------|
| `docs/ARCHITECTURE.md` | This file — authoritative build plan | Living |
| `docs/CONSTRAINTS.md` | Hierarchical decision framework | Stable |
| `docs/COMPONENT_SPEC.md` | Component-level specs + interfaces | Reference (superseded by this doc for strategy) |
| `docs/STATE.md` | Implementation status + session log | Updated each session |
| `docs/CONTINUE.md` | Session continuation prompt | Updated each session |
| `docs/ADR_002_MEANING_AT_READ_TIME.md` | Meaning-at-read-time decision | Stable |