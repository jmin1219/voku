# Voku — User Model Architecture (Integrated v2)

**Created:** 2026-02-21
**Status:** Design document for Build 4. Integrates: agentic reasoning literature, Seven Domains analysis, breathing architecture (Feb 16), multi-context consolidation (Feb 16), collaborative taxonomy (Feb 16-18), goal-as-evidence (Jan 30 – Feb 17), emergent structure principle (Feb 18), and 30+ prior architectural conversations.
**Replaces:** v1 design (pure probabilistic inference frame with 13 frozen dimensions, archived to `docs/archive/USERMODEL_v1.md`).

---

## The Shift

Builds 1–3 proved the loop: chat → extract → embed → retrieve → assemble context → chat. But the system has no unified understanding of the user — only 425 scattered observations. There is no inference layer that says "given all evidence, here is what I believe about this person, and here is what I don't know."

Build 4 adds that layer. Propositions become **evidence**. The user model is the **inference** over that evidence. The breathing architecture maps directly: inhale stores propositions (evidence), exhale runs inference (updates the model).

### Formal framing

POMDP formulation (Wei et al., "Agentic Reasoning for LLMs," Jan 2026 §2.2): the user is part of latent environment state X — unobservable, inferred from observations O. Voku maintains a belief state over X through updating. Each conversation is an observation that shifts the posterior.

Neural compositionality (THEORY.md §4): user model dimensions are reusable orthogonal modules. Context assembly is the gain control mechanism — amplifies relevant dimensions, suppresses irrelevant ones based on query intent. Uncertainty increases gain for adjacent dimensions.

### Integration with breathing architecture (Feb 16)

> "The consolidation scheduler replays accumulated propositions through N most recently active goal contexts. Propositions that activate across multiple contexts get entrenchment boost."

Build 4's exhale operationalizes this: each dimension is evaluated against its evidence AND against active goals. A dimension adjacent to multiple active goals gets priority in context assembly. This bridges the "derivative of productivity planning" insight (Jan 30): goals give meaning to data, data gives evidence about goals.

### Integration with collaborative taxonomy (Feb 16-18)

> "Module nodes = collaborative taxonomy. System suggests clusters from co-activation. User names, confirms, adjusts."

Dimensions are not frozen at design time. The emergent structure principle (Feb 18) governs: "data points arrive with geometric properties... structure self-organizes." Seed dimensions are coarse universal categories. Subdimensions emerge from propositional density. The system proposes splits. The user confirms.

---

## Seed Dimensions

Four universal categories derived from the natural fault lines in reflective writing. These are coarse enough to accommodate any user — a student, a retiree, a new parent, a founder. All meaningful subdimensions emerge from data.

| ID | Name | Description (used in assignment prompts) | Decay Class |
|----|------|------------------------------------------|-------------|
| `self` | Internal world | Identity, values, self-concept, emotional life, psychological patterns, how the person thinks, copes, regulates, and grows. Who they are when no one is watching. | core |
| `pursuits` | External direction | Career, projects, goals, plans, skills, creative work, learning-in-service-of-doing. What the person is building and working toward. | preference |
| `relationships` | Social world | Connections, family, friends, romantic life, social needs, relational patterns and history. How the person relates to other people. | preference |
| `body` | Physical reality | Health, fitness, energy, nutrition, sleep, physical state, limitations, embodied experience. What the body enables and constrains. | situational |

### Design rationale

**4 seeds, not 13.** The original 13 dimensions were derived from one user's propositional density in February 2026 — taxonomy disguised as emergence. These 4 represent the natural joints in reflective writing that hold across people and life stages. Subdimensions emerge through density detection, not developer intuition.

**Why these four:** A proposition about rest-as-defeat is unambiguously `self`. A proposition about Voku architecture is unambiguously `pursuits`. A proposition about missing social connection is `relationships`. A proposition about orthostatic symptoms is `body`. The assignment LLM makes trivially easy decisions at this level. Hard structural questions (is this identity-as-vocation or identity-as-self-concept?) are answered by emergence, not classification.

**Why not 5+:** Learning is always in service of something — it maps to whichever seed it serves. Finance, spirituality, creativity — these are real life domains but not universal seed-level categories. For users who journal heavily about them, they emerge from uncategorized density. The system discovers them rather than presupposing them.

**Subdimension emergence example (Jaymin's data):**
- `self` (~83 props) → DBSCAN finds clusters around self-evaluation/identity vs daily coping/regulation → system proposes split → user names them
- `pursuits` (~184 props) → massive Voku cluster + career direction cluster + academics cluster → system proposes 3 subdimensions
- `relationships` (~39 props) → may stay unified or split into current needs vs historical patterns
- `body` (~31 props) → may stay unified at this density
- ~88 uncategorized → some genuinely unmappable, some form micro-clusters (finance ~5 props) that don't yet meet density threshold

**Subdimension emergence example (stranger's Reddit data):**
- `self` → "identity transition" + "coping mechanisms"
- `pursuits` → stays career-focused or splits into career + creative hobby
- `relationships` → "partner dynamic" + "parenting"
- `body` → dominated by sleep deprivation
- New dimension emerges: domesticity/home management (doesn't fit any seed)

### Decay classes

From Seven Domains §3:
- **Core (months):** Identity beliefs, deep patterns. Prior widens slowly without contradicting evidence.
- **Preference (weeks):** Directional commitments, strategies. Decay moderately, need periodic refreshing.
- **Situational (days/hours):** Current state, energy, mood. Decay fast, represent ephemeral conditions.

Subdimensions inherit their parent's decay class by default but can be overridden (a subdimension of `self` about current coping strategies might be `preference` rather than `core`).

---

## Evidence Mode: Memories as Dual Evidence

When a user says "I went to 9 schools K-12," two pieces of evidence arrive in one proposition:

**Evidence about the past:** The biographical fact. Event time is childhood. Informs core dimensions with long time horizons.

**Evidence about the present:** The act of surfacing this memory now, in this context. The memory was recruited by the user's current psychological state. The *when* and *why* of memory introduction is evidence about what's psychologically active today.

The same childhood memory surfaced during career anxiety vs. during late-night vulnerability means different things for the model — not about what happened in childhood, but about what's alive for the person right now.

### Schema addition

```sql
-- On propositions table (already has event_timeframe and created_at)
ALTER TABLE propositions ADD COLUMN evidence_mode TEXT DEFAULT 'experiential';
-- 'experiential': present/recent (user did/felt/decided this)
-- 'retrospective': recounting history (user is narrating past events)
```

Classification is lightweight — the extraction LLM infers from temporal cues ("growing up," "when I was," "back in 2020" → retrospective; present tense, recent events → experiential).

### How the exhale uses evidence_mode

- **Experiential propositions:** Direct evidence about current state. Full relevance weight.
- **Retrospective propositions:** Dual evidence. Biographical content updates core dimensions. Introduction context (which conversation, what else was being discussed) logged in reasoning_trace — "user surfaced childhood instability memory while discussing career anxiety, suggesting connection between early experience and professional self-doubt."
- **Temporal view:** Retrospective propositions plotted at *introduction time* (when they entered the system), not event time. Optional biographical view plots at event time ("my life as I've narrated it" vs "my thinking as it evolved").

---

## Schema

### `user_model` table

```sql
CREATE TABLE IF NOT EXISTS user_model (
    id TEXT PRIMARY KEY,              -- e.g. 'self' or 'self.regulation' (after emergence)
    dimension TEXT NOT NULL,           -- e.g. 'self'
    subdimension TEXT,                 -- NULL for seed dimensions, e.g. 'regulation' after split
    description TEXT NOT NULL,         -- what this dimension tracks (used in assignment prompts)
    estimate TEXT NOT NULL,            -- natural language: current best understanding
    confidence REAL NOT NULL,          -- 0.0 (no evidence) to 1.0 (highly consistent evidence)
    uncertainty_type TEXT DEFAULT 'sparse',  -- 'sparse' | 'conflicted' | 'stable'
    evidence_count INTEGER DEFAULT 0,
    last_updated TEXT NOT NULL,
    last_evidence_at TEXT,             -- timestamp of most recent supporting proposition
    decay_class TEXT NOT NULL,         -- 'core' | 'preference' | 'situational'
    decay_rate REAL,                   -- learned from data, not fixed
    goal_relevance TEXT DEFAULT '[]',  -- JSON: active goal proposition IDs this dimension connects to
    status TEXT DEFAULT 'active',      -- 'active' | 'proposed' | 'retired'
    proposed_from TEXT,                -- if status='proposed': 'cluster_detection' | 'user_request' | 'split'
    parent_id TEXT,                    -- if this is a subdimension, FK to parent seed dimension
    summary_history TEXT DEFAULT '[]', -- JSON: previous estimates with timestamps (belief evolution)
    reasoning_trace TEXT               -- LLM's explanation: which evidence, what changed, what's uncertain
);
```

### `model_evidence` junction table

```sql
CREATE TABLE IF NOT EXISTS model_evidence (
    model_id TEXT NOT NULL,            -- FK to user_model.id
    proposition_id TEXT NOT NULL,      -- FK to propositions.id
    relevance REAL DEFAULT 0.5,        -- how strongly this proposition informs this dimension
    direction TEXT DEFAULT 'supports', -- 'supports' | 'contradicts' | 'contextualizes'
    assigned_at TEXT NOT NULL,
    assigned_by TEXT DEFAULT 'exhale', -- 'exhale' | 'manual' | 'extraction'
    PRIMARY KEY (model_id, proposition_id),
    FOREIGN KEY (model_id) REFERENCES user_model(id),
    FOREIGN KEY (proposition_id) REFERENCES propositions(id)
);
```

### Changes from v1

- **4 seed dimensions** replace 13 frozen dimensions — universal, coarse, emergence handles the rest
- **`description`** stored as data — used in assignment prompts, can be refined by exhale
- **`subdimension`** nullable — NULL for seeds, populated after emergence/split
- **`parent_id`** added — links subdimensions to their seed parent
- **`goal_relevance`** — tracks active goal connections per dimension
- **`status`** — enables lifecycle (active/proposed/retired)
- **`proposed_from`** — provenance for proposed dimensions
- **`evidence_mode`** on propositions table — experiential vs retrospective

### Why `uncertainty_type` matters

From Seven Domains (Dempster-Shafer): "Distinguish ignorance from balanced uncertainty."

- **sparse**: Few propositions, wide prior. System hasn't learned enough. → Active probing is high value.
- **conflicted**: Multiple propositions that disagree. User may be in transition. → Probing should be gentle, exploratory.
- **stable**: Multiple consistent propositions, narrow prior. → No probing needed; use freely in context assembly.

### Threshold gating on `summary_history`

LLM outputs are stochastic. Without gating, `summary_history` records noise as signal — the temporal view (the novel contribution) shows artifacts of sampling variance.

**Gate conditions — ALL must be met to record a change:**
1. **Semantic delta:** Embedding similarity between old estimate and new estimate < 0.9
2. **Confidence delta:** |old_confidence - new_confidence| > 0.1
3. **Evidence citation:** reasoning_trace must reference specific proposition IDs

Implements gain-limiting from Seven Domains: "Cap the maximum rate of change the system reports."

---

## Processes

### 0. DB Consolidation (prerequisite)

Merge `m2_conversation.db` + `voku.db` → single `voku.db`. One DB, one config, one connection pattern. Required before adding more tables.

### 1. Assignment (proposition → model) — TWO-PASS

**When:** After extraction stores new propositions (end of inhale).

**Pass 1 — Classification (which dimensions?):**
- Input: proposition text + conversation context + list of active dimensions with descriptions
- Output: 0–3 dimension IDs per proposition
- Prompt: "What does this proposition tell you about this person? Which aspects of their life does it inform?" (not "what category?")
- With 4 coarse seeds, this is trivially easy — almost no classification errors

**Pass 2 — Scoring (relevance + direction):**
- Input: proposition text + assigned dimension descriptions + existing evidence for those dimensions
- Output: relevance (0-1) and direction (supports/contradicts/contextualizes) per assignment

**Evidence mode:** Extraction prompt classifies `evidence_mode` alongside existing fields. Lightweight — temporal cues are reliable signals.

### 2. Exhale (inference over evidence) — MULTI-GOAL

**When:** After assignment completes. Also on decay schedule.

**How:** For each dimension with new evidence or crossed decay threshold:

1. Gather all propositions from `model_evidence`, ordered by time
2. Weight by evidence_mode: experiential = full weight, retrospective = full weight for core dimensions, reduced for situational
3. Include current estimate and confidence
4. Identify active goals (recent intention-type propositions with high confidence)
5. Compute goal adjacency → update `goal_relevance`
6. LLM inference call:
   - Evidence summary + current state + related goals
   - "Cite specific proposition IDs supporting your assessment"
   - For retrospective evidence: "Note why the user surfaced this memory in this context"
7. **Threshold gate:** semantic delta + confidence delta + evidence citation. If gate fails → log, don't commit.
8. If gate passes → update estimate, append old to `summary_history`
9. Flag conflicted if new evidence contradicts current estimate

**Cross-context entrenchment (from Feb 16):**
After per-dimension exhale, compute cross-goal activation. Propositions serving dimensions connected to 3+ active goals → entrenchment boost in `model_evidence.relevance`.

**Decay without new evidence:**
- Core: ~2%/week confidence decrease
- Preference: ~5%/week
- Situational: ~20%/day
- Starting points — system learns actual rates from data

### 3. Emergence Detection

**Trigger:** After assignment batch completes.

**Dimension split (within existing dimension):**
- For each seed dimension with 30+ assigned propositions
- Run DBSCAN on those propositions' embeddings (eps=0.7, min_samples=10)
- If 2+ distinct clusters found → propose split
- Insert proposed subdimensions with `status='proposed'`, `parent_id` set, descriptions auto-generated from cluster keywords
- User confirms/rejects via UI or conversation

**New dimension (from uncategorized):**
- Get all propositions with 0 assignments in model_evidence
- Run DBSCAN (eps=0.7, min_samples=10)
- Clusters exceeding threshold → propose new top-level dimension
- Same confirmation flow

**Retirement:**
- No new evidence for 2+ months AND confidence below 0.2 → suggest retirement
- User explicitly retires
- Retired dimensions preserved in `summary_history` for temporal view

### 4. Context Assembly — INVERSE CONFIDENCE WEIGHTING

**Layer 1 — Model state (new):**

Identify relevant dimensions (embedding similarity between query and dimension descriptions). Apply inverse confidence weighting:

- **Sparse/conflicted** (low confidence): Full treatment — estimate, evidence summary, uncertainty type, what's unknown
- **Stable** (high confidence): One-line summary
- **Goal-adjacent + uncertain**: Boosted priority regardless of query similarity

Token budget: ~300 tokens for model state. Inverse weighting self-manages — well-understood dimensions compress, uncertain ones expand.

```
## Your understanding of this user

**External direction** (moderate confidence, goal-adjacent: "Fall 2026 co-op"):
Consolidating around AI engineering. Timeline unclear — evidence sparse on
specific companies. User recently surfaced childhood instability memories while
discussing career positioning, suggesting identity formation connects to
professional anxiety.

**Internal world** (partially stable):
Strong pattern recognition around self-regulation (morning formula, afternoon murk).
Self-concept area is conflicted — recent evidence shows tension between
"build to help others see themselves" and performance anxiety.

**Areas needing more information:**
- Financial dimension (5 data points, no subdimensions emerged)
- Physical state (last evidence 5 days ago, confidence decaying)

When naturally relevant, create space for the user to elaborate in uncertain areas.
Do not interrogate. Let curiosity emerge from the conversation.
```

**Layer 2 — Proposition evidence (existing, annotated with dimension):**
Retrieved propositions as before, annotated with which dimension they serve. LLM sees model summary + raw evidence. Token budget: ~400 tokens.

### 5. Phase Space Reinterpretation

**Topical view = What the system knows:**
Propositions colored by seed dimension (4 colors). Subdimensions get shade variants of parent color. Uncategorized propositions get neutral gray. Proposed dimensions rendered with dashed boundary, muted color.

Density = confidence. Tight bright cluster = system understands well. Sparse scattered cloud = system barely knows. Users literally see where they're understood and where they're not.

**Temporal view = How understanding developed:**
`summary_history` renders as trajectories through time. Threshold gating ensures only real changes appear. Retrospective propositions plotted at introduction time (default) or event time (biographical mode).

Shows: emergence (sparse → stable), transition (stable → conflicted → new-stable), dying ideas (faded, no longer load-bearing), subdimension births (the moment a seed split into specific understanding).

**Model view (stretch) = Uncertainty landscape:**
Dimensions as heatmap. Hot/bright = confident. Cool/dim = sparse/conflicted. Goal-adjacent dimensions highlighted. The user sees their known unknowns — especially relative to what they're trying to do.

### 6. Sensitive Data Routing

| Process | Sensitivity | Preferred Provider |
|---------|------------|-------------------|
| Chat (streaming) | Medium | Cloud (Anthropic) |
| Extraction | Medium | Cloud (Groq) or local |
| Assignment Pass 1 | Low | Cloud (Groq) |
| Assignment Pass 2 | Medium | Cloud (Groq) |
| Exhale inference | High | Local (Ollama) preferred |

Sensitivity budget for context assembly: propositions in `self` dimension get higher sensitivity scores. If total exceeds threshold, prefer model summaries over raw evidence in cloud API calls.

---

## Dimension Lifecycle

```
[Empty DB]
    ↓ seed
[4 active seed dimensions, all sparse, confidence 0.0]
    ↓ conversations accumulate → extraction → assignment
[Seeds accumulate evidence, confidence rises]
    ↓ density exceeds threshold within a seed
[System proposes subdimension split]
    ↓ user confirms
[Parent + children coexist; parent becomes summary, children get evidence]
    ↓ continued accumulation
[Some subdimensions stabilize, others stay sparse, new ones proposed]
    ↓ uncategorized cluster forms
[System proposes new top-level dimension]
    ↓ user names and confirms
[Taxonomy grows organically]
    ↓ user's life changes
[Old subdimension stops receiving evidence → confidence decays → retirement suggested]
```

---

## Cold Start

**Phase A (0-5 conversations, <20 propositions):**
- All 4 seeds at sparse/0.0. No assignment or exhale runs.
- System behaves as normal chatbot. Phase space shows empty state.

**Phase B (5-15 conversations, 20-100 propositions):**
- First assignment batch. Propositions map to seeds.
- First exhale: tentative estimates, low confidence.
- Context assembly injects sparse model state → LLM becomes more curious.
- Phase space shows colored regions forming.

**Phase C (15+ conversations, 100+ propositions):**
- Emergence detection starts finding subdimension clusters.
- Some dimensions stabilize, others still sparse → uncertainty texture.
- Active probing works: system asks better questions in uncertain areas.
- Phase space shows real structure with proposed splits.

**Phase D (50+ conversations, 300+ propositions):**
- Multiple subdimensions confirmed. Taxonomy reflects actual user.
- Temporal view shows belief trajectories with real history.
- Model view shows meaningful uncertainty landscape.

---

## Principles Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| Conversation is cognition | ✅ | Self-discovery emergent from substrate, not engineered. 4 coarse seeds + emergence. |
| Emergent structure | ✅ | Subdimensions emerge from density, not classification. Assignment is trivially easy (4 categories). |
| Broad storage, narrow retrieval | ✅ | Propositions unchanged. Assignment in junction table (org space), not on proposition (user space). |
| Don't over-classify at ingestion | ✅ | 4 coarse categories = minimum viable classification. Hard questions answered by emergence. |
| Goals give meaning to data | ✅ | Multi-goal exhale. Goal adjacency per dimension. Inverse confidence weighting prioritizes goal-adjacent uncertainty. |
| The user is the loop | ✅ | User confirms proposed dimensions, sees reasoning traces, can reject. System proposes, user validates. |
| Model of me, not model of notes | ✅ | Dimensions describe aspects of a life, not topics of conversation. |
| Observer paradox | ⚠️ | Gain-limiting (threshold gating) prevents over-reporting. System language uses "here's what I've noticed" not definitive assessments. Philosophical tension acknowledged — "co-creates a useful model of who they're becoming." |
| Bi-temporal standard (Graphiti) | ✅ | event_timeframe + created_at + evidence_mode. Retrospective vs experiential distinction operational. |

---

## Build Sequence

| Piece | What | Sessions | Notes |
|-------|------|----------|-------|
| 0 | DB consolidation | 0.5 | Merge two DBs → one voku.db |
| 1 | Schema + seed (4 dimensions, evidence_mode column) | 0.5 | Tables + seed script with generic defaults + personal override |
| 2 | Assignment Pass 1 (classify to 4 seeds) | 1 | Trivially easy classification |
| 2b | Assignment Pass 2 (relevance + direction) | 0.5 | Narrower context, better judgment |
| 5* | Phase space recolor by dimension | 1 | **Moved up.** Visual validation of assignment quality. |
| 3 | Exhale (multi-goal inference, threshold gating, evidence_mode handling) | 1–2 | Core inference with all gates |
| 3b | Emergence detection (split proposals + uncategorized clustering) | 0.5–1 | DBSCAN on per-dimension evidence |
| 4 | Context assembly v2 (inverse-confidence, goal-adjacent boosting) | 1 | Token-budgeted system prompt |
| 6 | Temporal trajectories (gated summary_history, retrospective handling) | 1 | Biographical vs introduction time modes |
| 7 | Model view — uncertainty heatmap | 1 | Stretch goal |

**Total: 8–10 sessions → late March → before Mar 31 demo.**

### Demo narrative (Mar 31)

"This is Voku. I've been thinking out loud through it for three months."

1. Open the app. Four broad colored regions — my inner world, my pursuits, my relationships, my body. But within pursuits, you can see the system discovered three sub-regions on its own: Voku, career direction, academics. I named them when it asked.
2. Start a conversation about something uncertain — career positioning, which connects to an active goal. The system's response is more curious, more exploratory. It noticed I surfaced a childhood memory while discussing career anxiety last week, and it's gently probing whether that connection is real.
3. Temporal view. Trace how "pursuits" started as one blob and differentiated over weeks. See the moment career direction consolidated. See dying ideas — the earlier product concepts — still visible but faded. Every trajectory point backed by evidence.
4. Contradict something. Watch confidence shift. The system can show you exactly which evidence changed its mind. The reasoning is transparent, not a black box.

"The system started with four blank categories and zero knowledge. Everything you see — the structure, the subdimensions, the understanding — emerged from conversation. A different person's Voku would look completely different, because it would reflect their life, not mine."