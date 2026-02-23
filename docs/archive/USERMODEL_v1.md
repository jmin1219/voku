# Voku — User Model Architecture

**Created:** 2026-02-21
**Status:** Build 4 design. Integrated from 30+ architectural conversations, agentic reasoning literature, Seven Domains analysis, breathing architecture, collaborative taxonomy, and multi-context consolidation patterns.

---

## The Shift

Builds 1–3 proved the loop: chat → extract → embed → retrieve → assemble context → chat. Propositions are stored and retrieved. But the system has no unified understanding of the user — only scattered observations. There is no inference layer that says "given all evidence, here is what I believe about this person, and here is what I don't know."

Build 4 adds that layer. Propositions become **evidence**. The user model is the **inference** over that evidence. The breathing architecture maps directly: inhale stores propositions (evidence), exhale runs inference (updates the model).

### Formal framing

Following the POMDP formulation (Wei et al., "Agentic Reasoning for LLMs," Jan 2026 §2.2): the user is part of the latent environment state X — unobservable, inferred from observations O (what the user says and does). Voku maintains a belief state over X through updating. Each conversation is an observation that shifts the posterior.

Neural compositionality (THEORY.md §4): the user model dimensions are reusable orthogonal modules. Context assembly is the gain control mechanism — it amplifies relevant dimensions and suppresses irrelevant ones based on current query intent. Uncertainty increases gain when the conversation topic is adjacent.

### Integration with breathing architecture

The exhale is not single-context. Each dimension is evaluated against its evidence AND against active goals. A dimension adjacent to multiple active goals gets priority in context assembly. This bridges the core insight: goals give meaning to data, data gives evidence about goals.

### Integration with collaborative taxonomy

Dimensions are not frozen at design time. The seed dimensions are coarse and universal. Subdimensions emerge from propositional density via cluster detection. The system proposes, the user confirms or dismisses. Structure self-organizes rather than being imposed.

---

## Seed Dimensions

Four coarse dimensions, designed to be universal across users. Subdimensions emerge from data.

| ID | Name | Description | Decay Class |
|----|------|-------------|-------------|
| `self` | Internal world | Identity, values, self-concept, emotional life, psychological patterns, how the person thinks, copes, regulates, and grows. Who they are when no one is watching. | core (months) |
| `pursuits` | External direction | Career, projects, goals, plans, skills, creative work, learning-in-service-of-doing. What the person is building and working toward. | preference (weeks) |
| `relationships` | Social world | Connections, family, friends, romantic life, social needs, relational patterns and history. How the person relates to other people. | preference (weeks) |
| `body` | Physical reality | Health, fitness, energy, nutrition, sleep, physical state, limitations, embodied experience. What the body enables and constrains. | situational (days) |

### Why four

**Universal fault lines.** These four map to reflective writing regardless of who the writer is. A retiree, a new parent, a student, a founder — all generate propositions that cleanly sort into internal world, pursuits, relationships, and body. The assignment LLM makes a trivially easy decision (which of four?), not a hard one (which of thirteen?).

**Emergence handles the rest.** After enough propositions accumulate in a seed dimension, DBSCAN detects subclusters. The system proposes splits. Example: `self` accumulates 80+ propositions, two clusters emerge — one around self-evaluation/identity, another around daily coping/regulation. System proposes splitting. User names the subdimensions. The taxonomy grows from data, not from developer intuition.

**No anchor bias.** With 13 predetermined dimensions, the assignment LLM assigns propositions to categories that *exist* even when the fit is marginal. Categories attract content. With 4 coarse seeds, marginal assignments are rare because the boundaries are obvious. The interesting structural questions are answered by density, not classification.

### What emergence discovers

The system monitors uncategorized propositions and within-dimension subclusters. When semantic density exceeds threshold (DBSCAN, same parameters as existing phase space clustering):

- **Within-dimension split:** `pursuits` bifurcates into career-focused and project-focused clusters → system proposes two subdimensions
- **New dimension:** Uncategorized propositions form a dense cluster around finance/money → system proposes a new top-level dimension
- **Retirement:** A subdimension receives no new evidence for 2+ months and confidence drops below 0.2 → system proposes retirement

The user confirms, names, adjusts, or dismisses every proposal.

### Decay classes

From Seven Domains §3:
- **Core (months):** Identity beliefs, deep patterns — don't decay without contradicting evidence. Prior widens slowly (~2%/week).
- **Preference (weeks):** Directional commitments, strategies, current orientations — decay moderately (~5%/week), need periodic refreshing.
- **Situational (days/hours):** Current state, energy, mood — decay fast (~20%/day), represent ephemeral conditions.

Rates are starting points. The system should learn actual decay rates from data over time.

---

## Evidence Modes

A proposition carries two kinds of evidence depending on whether the user is describing the present or recounting history.

### The distinction

**Experiential:** The user did, felt, or decided this in the present or recent past. "I skipped my workout again today." Direct evidence about current state and behavior. Full weight for all dimensions.

**Retrospective:** The user is recounting something from their history. "I moved around a lot as a kid." This is dual evidence:

1. **Biographical content** — the historical fact. Informs core-decay dimensions (identity, relational history) with long time horizons.
2. **Introduction context** — the fact that this memory was surfaced *now, in this conversation, in this context*. The memory was recruited by the user's current psychological state. This is situational evidence about what's active for the person right now.

### Schema addition

```sql
-- On propositions table (already has event_timeframe and created_at)
evidence_mode TEXT DEFAULT 'experiential'
-- 'experiential' (present/recent) | 'retrospective' (recounting history)
-- Classified during extraction from temporal cues
```

### How it affects the pipeline

**Extraction:** The extraction prompt already produces `event_timeframe`. Adding `evidence_mode` is lightweight — the LLM infers it from temporal cues ("growing up," "when I was," "back in 2020" → retrospective).

**Assignment:** Both modes assign to dimensions normally. A retrospective proposition about childhood instability assigns to `self` and `relationships` just like an experiential one would.

**Exhale:** Retrospective propositions update core dimensions with biographical content. But the reasoning trace also notes the introduction context: "User surfaced this childhood memory during a conversation about career anxiety, suggesting a connection between early instability and professional self-doubt."

**Phase space temporal view:** Two rendering modes for retrospective propositions:
- **Default:** Plotted at introduction time (when the evidence entered the system). This preserves the "how understanding developed" narrative.
- **Biographical view (future):** Plotted at event time. "My life as I've narrated it to Voku" — a separate projection showing the user's story in chronological order.

---

## Schema

### `user_model` table

```sql
CREATE TABLE IF NOT EXISTS user_model (
    id TEXT PRIMARY KEY,              -- e.g. 'self' or 'self.regulation'
    dimension TEXT NOT NULL,           -- top level: e.g. 'self'
    subdimension TEXT,                 -- e.g. 'regulation' (NULL for seed dimensions)
    description TEXT NOT NULL,         -- used in assignment prompts and context assembly
    estimate TEXT NOT NULL,            -- natural language: current best understanding
    confidence REAL NOT NULL,          -- 0.0 to 1.0
    uncertainty_type TEXT DEFAULT 'sparse',  -- 'sparse' | 'conflicted' | 'stable'
    evidence_count INTEGER DEFAULT 0,
    last_updated TEXT NOT NULL,
    last_evidence_at TEXT,
    decay_class TEXT NOT NULL,         -- 'core' | 'preference' | 'situational'
    decay_rate REAL,                   -- learned from data
    goal_relevance TEXT DEFAULT '[]',  -- JSON: active goal proposition IDs this dimension connects to
    status TEXT DEFAULT 'active',      -- 'active' | 'proposed' | 'retired'
    proposed_from TEXT,                -- if proposed: 'cluster_detection' | 'user_request' | 'exhale_detection'
    parent_id TEXT,                    -- FK to parent dimension (NULL for seeds, parent ID for subdimensions)
    summary_history TEXT DEFAULT '[]', -- JSON: previous estimates with timestamps (belief evolution)
    reasoning_trace TEXT               -- LLM explanation: which evidence, what changed, what's uncertain
);
```

### `model_evidence` junction table

```sql
CREATE TABLE IF NOT EXISTS model_evidence (
    model_id TEXT NOT NULL,            -- FK to user_model.id
    proposition_id TEXT NOT NULL,      -- FK to propositions.id
    relevance REAL DEFAULT 0.5,        -- how strongly this informs this dimension
    direction TEXT DEFAULT 'supports', -- 'supports' | 'contradicts' | 'contextualizes'
    assigned_at TEXT NOT NULL,
    assigned_by TEXT DEFAULT 'exhale', -- 'exhale' | 'manual' | 'extraction'
    PRIMARY KEY (model_id, proposition_id),
    FOREIGN KEY (model_id) REFERENCES user_model(id),
    FOREIGN KEY (proposition_id) REFERENCES propositions(id)
);
```

### Key design decisions

**`parent_id` enables the hierarchy.** Seed dimensions have `parent_id = NULL`. Subdimensions link to their parent. When `self` splits into `self.identity` and `self.regulation`, both point back to `self`. The parent can retire or remain as an umbrella.

**`subdimension` is NULL for seeds.** This distinguishes top-level seeds from emerged subdimensions in queries without traversing parent_id.

**`description` is mutable.** Seed descriptions start generic. As evidence accumulates, the exhale can refine descriptions to reflect what the system has actually learned. For a new user, `self` starts as "Identity, values, self-concept, emotional life..." For a user who journals heavily about perfectionism, the exhale might update to "Identity centered on perfectionism patterns, self-evaluation cycles, and the gap between stated values and revealed behavior."

### Threshold gating on `summary_history`

LLM outputs are stochastic. Without gating, `summary_history` records noise as signal — the temporal view shows artifacts of sampling variance, not real belief evolution.

**Gate conditions (all three must be met):**
1. **Semantic delta:** Embedding similarity between old and new estimate < 0.9
2. **Confidence delta:** |old_confidence - new_confidence| > 0.1
3. **Evidence citation:** `reasoning_trace` must reference specific proposition IDs

This implements gain-limiting (Seven Domains): cap the rate of change the system reports. Noise doesn't cross the threshold. Real belief shifts do.

### Why `uncertainty_type` matters

From Seven Domains (Dempster-Shafer): distinguish ignorance from balanced uncertainty.

- **sparse**: Few propositions, wide prior. Not enough data. → Active probing is high value.
- **conflicted**: Multiple propositions, but they disagree. → User may be in transition. Probe gently.
- **stable**: Consistent propositions, narrow prior. → Use freely; no probing needed.

---

## Processes

### 0. DB Consolidation (prerequisite)

Two databases creates cross-reference problems. The exhale needs propositions, conversation timestamps, session metadata, and model state in the same transactional scope.

**Action:** Merge `m2_conversation.db` + `voku.db` → single `voku.db`. Update `config.py` to single `db_path`. ~30 minutes.

### 1. Assignment — TWO-PASS

**When:** After extraction stores new propositions (end of inhale).

**Pass 1 — Classification (which dimensions?):**
- Input: proposition text + conversation context + list of active dimensions with descriptions
- Output: 0–3 dimension IDs per proposition
- Prompt framing: "What does this proposition tell you about this person? Which aspects of their life does it inform?"
- Propositions can map to 0 dimensions (specific code decisions, one-off observations join the uncategorized pool)

**Pass 2 — Scoring (relevance + direction):**
- Input: proposition text + assigned dimension descriptions + existing evidence sample
- Output: relevance (0-1) and direction (supports/contradicts/contextualizes) per assignment
- Narrower context = better judgment

**Technical:** Two Groq calls per batch. Structured JSON output.

### 2. Emergence Detection

**When:** After assignment. Also periodically (weekly).

**Within-dimension splits:**
- For each dimension with 15+ evidence propositions, run DBSCAN on their embeddings
- If 2+ distinct clusters found: propose split. Generate subdimension descriptions from cluster keywords.
- Insert proposed subdimensions with `status='proposed'`, `parent_id` pointing to parent

**New dimension from uncategorized:**
- Gather all propositions with 0 assignments
- Run DBSCAN (eps=0.7, min_samples=10)
- Dense clusters → propose new top-level dimension

**User flow:** Proposed dimensions surface in the UI with distinct visual treatment. User confirms (→ active), renames, or dismisses (→ deleted or retired).

### 3. Exhale (inference) — MULTI-GOAL, THRESHOLD-GATED

**When:** After assignment completes. Also on decay schedule.

For each dimension with new evidence or crossed decay threshold:

1. Gather evidence from `model_evidence`, ordered by time. Note `evidence_mode` (experiential vs retrospective).
2. Get current estimate + confidence.
3. Identify active goals: recent intention-type propositions with high confidence.
4. Compute goal adjacency → update `goal_relevance`.
5. LLM inference:
   - Evidence + current estimate + active goals
   - "What is the current best estimate? Has anything changed? Confidence level? Evidence consistent, insufficient, or contradictory?"
   - "**Cite specific proposition IDs.**"
   - For retrospective evidence: "Note why this historical memory was surfaced in its introduction context."
6. **Threshold gate:** embed old vs new estimate. If similarity > 0.9 AND confidence delta < 0.1 → skip. If no proposition IDs cited → skip.
7. If gate passes: commit update, append old estimate to `summary_history`.
8. Flag transitions: new evidence contradicts current estimate → set `uncertainty_type = 'conflicted'`.

**Cross-context entrenchment:** After per-dimension exhale, compute cross-goal activation. Propositions serving as evidence for dimensions connected to 3+ active goals get entrenchment boost in `model_evidence.relevance`.

### 4. Context Assembly — INVERSE CONFIDENCE WEIGHTING

**Layer 1 — Model state (~300 tokens max):**

Relevant dimensions identified by query similarity. Inverse confidence weighting:

- **Sparse/conflicted** (low confidence): Full treatment — estimate, evidence summary, uncertainty, what's unknown
- **Stable** (high confidence): One-line summary
- **Goal-adjacent + uncertain**: Boosted priority regardless of query similarity

```
## Your understanding of this user

**[Dimension]** (confidence level, goal context if relevant):
[estimate]. Uncertainty: [what's unknown or conflicted].

**[Stable dimension]**: [one-line summary].

**Areas needing more information:**
- [sparse dimension with context]

When naturally relevant, create space for the user to elaborate in uncertain areas.
Do not interrogate. Let curiosity emerge from the conversation.
```

**Layer 2 — Proposition evidence (~400 tokens max):**
Retrieved propositions annotated with dimension membership. LLM sees both model summary and raw evidence.

### 5. Dimension Lifecycle

**Proposal → Confirmation → Active → (optional) Split or Retirement**

- Proposals come from: emergence detection, user request, exhale pattern detection
- Confirmation requires user action (API endpoint + UI)
- Retirement triggers: no evidence 2+ months + confidence < 0.2, explicit user retirement, or replacement by split children
- Split: parent can retire or remain as umbrella. Children inherit relevant evidence via reassignment.

---

## Phase Space Reinterpretation

**Topical view = What the system knows:**
Propositions colored by dimension membership. Density = confidence. Proposed dimensions rendered with distinct treatment (dashed boundary, muted color). Uncategorized propositions in neutral color — the emergence signal.

**Temporal view = How understanding developed:**
Propositions at introduction time. `summary_history` trajectories overlaid. Only changes that passed threshold gate appear. Shows: emergence (sparse → stable), transition (stable → conflicted → new stable), dying ideas (evidence for shifted dimensions).

**Biographical view (future) = The user's story:**
Retrospective propositions plotted at event time. The life narrative as told to Voku, in chronological order.

**Model view (stretch) = The uncertainty landscape:**
Dimensions as heatmap. Hot/bright = confident. Cool/dim = sparse/conflicted. Goal-adjacent dimensions highlighted. Known unknowns made visible.

---

## Sensitive Data Routing

| Process | Sensitivity | Preferred Provider |
|---------|------------|-------------------|
| Chat (streaming) | Medium | Cloud (Anthropic) |
| Extraction | Medium | Cloud (Groq) or local |
| Assignment Pass 1 | Low-medium | Cloud (Groq) |
| Assignment Pass 2 | Medium | Cloud (Groq) |
| Exhale inference | High | Local (Ollama) preferred |

Context assembly sensitivity budget: propositions serving identity/emotional dimensions get higher sensitivity scores. If total exceeds threshold, prefer model summaries over raw evidence in cloud API calls.

---

## Principles Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| Conversation is cognition | ✅ | Self-discovery emerges from substrate, not engineered |
| Emergent structure | ✅ | 4 coarse seeds, subdimensions from density, not classification |
| Broad storage, narrow retrieval | ✅ | Propositions unchanged; model_evidence is org-space overlay |
| Don't over-classify at ingestion | ✅ | 4-way classification is trivially easy; hard structure from emergence |
| Goals give meaning to data | ✅ | Multi-goal exhale, goal adjacency, inverse confidence weighting |
| The user is the loop | ✅ | User confirms proposals, sees reasoning traces, can reject |
| Model of me, not model of notes | ✅ | Dimensions describe life aspects, not conversation topics |
| Observer paradox | ⚠️ | Gain-limiting + informational framing mitigate. Co-construction acknowledged. |
| Day 3 ≠ Day 1 | ✅ | Model improves with every conversation |
| UI is load-bearing | ✅ | Phase space reinterpretation makes model visible |
| Single-file DB | ✅ | Consolidation is Piece 0 |

**2026 standards:**
- Bi-temporal modeling ✅ (event_timeframe + created_at + evidence_mode)
- Context engineering ✅ (inverse-confidence weighted, goal-adjacent, token-budgeted)
- POMDP framing ✅ (observations → latent state → belief update → policy)
- Memory taxonomy ✅ (flat → structured → experience per Wei et al.)
- Privacy-by-design ✅ (sensitive data routing, sensitivity budget)
- Automated evaluation ⚠️ (designed in eval playbook, not yet built)
- User model control UI ⚠️ (dimension confirmation exists, full correction UI is post-demo)

---

## Build Sequence

| Piece | What | Sessions | Notes |
|-------|------|----------|-------|
| 0 | DB consolidation | 0.5 | Merge into single voku.db |
| 1 | Schema + seed 4 dimensions | 0.5 | Tables + generic descriptions |
| 2 | Assignment Pass 1 (classification) | 1 | "What does this tell you about this person?" |
| 2b | Assignment Pass 2 (scoring) | 0.5 | Relevance + direction |
| 5* | Phase space recolor by dimension | 1 | **Moved up.** Visual validation of assignment quality. |
| 3 | Exhale (multi-goal, threshold-gated) | 1–2 | Goal adjacency + cross-context entrenchment |
| 4 | Context assembly v2 | 1 | Inverse confidence + token budget |
| 6 | Temporal trajectories | 1 | Gated summary_history rendering |
| 7 | Model view (stretch) | 1 | Uncertainty heatmap |

**Total: 7–9 sessions → mid-to-late March → before Mar 31 demo.**

---

## Cold Start

**Phase A (0-5 conversations, <30 propositions):** All 4 seeds are sparse, confidence 0.0. No assignment or exhale runs. Chat works normally without model context. Phase space shows empty state message.

**Phase B (5-15 conversations, 30-100 propositions):** First assignment batch. Propositions map to seeds. Phase space gains color. Exhale runs on dimensions with 5+ evidence. Estimates are tentative. Context assembly starts injecting sparse model state — LLM becomes more curious.

**Phase C (15+ conversations, 100+ propositions):** Emergence detection finds subclusters within seeds. Proposes splits. User names subdimensions. Model has texture — some stable, some sparse. Context assembly probes goal-adjacent uncertainty.

Seed descriptions start generic. The exhale refines them as evidence accumulates, adapting to whoever is using the system.

---

## Demo Narrative (Mar 31)

"This is Voku. I've been thinking out loud through it for three months."

1. Open the app. Colored regions — broad at first (self, pursuits, relationships, body), with subdivisions the system discovered from my data. Dense where it knows me well. Dim where it doesn't. A dashed region where something new might be forming.
2. Start a conversation near an active goal where the system is uncertain. The response is curious, exploratory — not asserting, but creating space.
3. Switch to temporal view. Trace how understanding consolidated over weeks. See the transition points. See dying ideas still visible but faded. Every trajectory point backed by evidence.
4. Say something that contradicts an existing belief. Watch confidence shift. The system can cite exactly which evidence changed its mind.

"The system doesn't just remember — it understands, questions, and shows you where it's still learning."
