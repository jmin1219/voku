# Voku v0.3: Complete Architecture Specification

> Last Updated: 2026-02-06
> Status: Architecture Finalized, Pre-Implementation
> Design Philosophy: Self-understanding as anchor, goals as emergent byproduct

---

## 1. Vision

### North Star
Build tools that help humans see themselves objectively — externalizing mental models that transform how people understand their own thinking.

### What Voku Is
A knowledge-first cognitive prosthetic that:
- Takes **conversation as primary input** (not manual note-taking)
- **Extracts structured beliefs** from natural speech
- **Organizes into a graph** anchored by user-declared intentions
- **Shows thinking evolving** over time — belief evolution is the core feature

### What Voku Is Not
- Another RAG chatbot (retrieval is a capability, not the product)
- A note-taking app with AI features (conversation-first, not text-first)
- An autonomous organizer (AI proposes, human confirms)
- A replacement for human judgment (externalization tool, not decision-maker)

### The One-Liner
"Voku extracts what you believe from what you say, shows you how your thinking connects, and lets you watch your mental model evolve."

### What Makes Voku Personal (Not a Knowledge Base)

Voku is not a productivity planner. Productivity planners take stated goals as input and track tasks toward them. Voku questions whether stated goals are *real* — or performance, or inherited, or outdated.

**The hierarchy is inverted:**
```
Productivity Planners:  Goals → Plans → Tasks → Tracking
Voku:                  Observations → Patterns → Self-Knowledge → (Goals emerge)
```

Goals aren't the anchor. **Self-understanding is the anchor.** Goals are a byproduct of seeing yourself clearly.

**Voku's core function:** Surface discrepancies between stated intentions and observed patterns. The gap between what you say you want and what your behavior suggests you want — that's where Voku provides unique value.

This is the derivative of productivity planning. It solves the root problems:

| Symptom | Root Problem Voku Surfaces |
|---------|----------------------------|
| "I can't stick to my plan" | Your plans assume a self that isn't you |
| "I keep procrastinating" | You avoid things that threaten your self-image |
| "I don't know what to prioritize" | Your stated priorities conflict with your revealed preferences |

**Information exists to serve decision-making, not to accumulate.** Every extracted belief should ultimately connect to understanding yourself better — your patterns, tendencies, real (not stated) preferences, and the gaps between intention and action.

---

## 2. Core Architectural Principles

### 2.1 Research Depth as Architectural Axis

> **⏸️ DEFERRED (Feb 06):** No documented friction from 60+ conversations maps to "I wish processing were lighter/deeper." All documented failures are about organization, temporal awareness, and compression mutation — not processing depth. Keep in design vision; implement after vertical slice validates core graph value. Build if usage reveals need.

Research depth is not a feature toggle — it's a fundamental dimension affecting every operation.

```
DEPTH 0-2: CAPTURE MODE
├── Store raw conversation turns as leaves
├── Minimal processing (embedding only)
├── No connection proposals
├── Use case: Quick notes, stream of consciousness

DEPTH 3-5: ACTIVE MODE (default)
├── Proposition extraction from turns
├── Connection finding to recent/similar nodes
├── Ghost proposals for obvious links
├── Basic abstraction detection
├── Use case: Normal conversation with Voku

DEPTH 6-8: SYNTHESIS MODE
├── Everything in Active, plus:
├── Keyword hierarchy construction
├── Cross-module bridge detection
├── Pattern identification across time
├── Proactive abstraction proposals
├── Use case: Intentional knowledge building

DEPTH 9-10: RESEARCH MODE
├── Everything in Synthesis, plus:
├── Contradiction detection and surfacing
├── Belief evolution analysis
├── Hypothesis generation ("You might also believe...")
├── Gap identification ("You've discussed X and Y but never Z")
├── External knowledge integration
├── Use case: Deep reflection, thesis development
```

**Depth Configuration:**
- Global default (user preference)
- Per-module override ("Career at depth 8, finance at depth 3")
- Per-session override ("Go deep on this conversation")

### 2.2 User Space vs Organization Space

Voku needs working memory separate from user's visible graph.

```
┌─────────────────────────────────────────────────────────────┐
│                      USER SPACE                              │
│                (What the user sees and confirms)             │
│                                                              │
│  Root Nodes (Modules) — User-declared focus areas            │
│  └── Internal Nodes — Confirmed abstractions                 │
│      └── Leaf Nodes — Extracted from conversation            │
│                                                              │
│  + Ghost Nodes — Suggestions awaiting confirmation           │
│    (graduated visibility: suggested → faded → rejected)      │
└─────────────────────────────────────────────────────────────┘
                            │
                    Voku promotes from
                    Organization Space
                            │
┌─────────────────────────────────────────────────────────────┐
│                   ORGANIZATION SPACE                         │
│              (Voku's hidden cognitive workspace)            │
│                                                              │
│  Compression Nodes — Weekly/monthly activity summaries       │
│  Priority Nodes — "What matters most right now"              │
│  Pattern Nodes — "These nodes form a theme" (pre-abstraction)│
│  Hypothesis Nodes — "Based on X,Y,Z you might believe W"     │
│  Keyword Nodes — MeSH-style hierarchy for connection finding │
│  Bridge Nodes — Cross-domain connection candidates           │
│                                                              │
│  Inspectable: User can ask "Why did you suggest this?"       │
└─────────────────────────────────────────────────────────────┘
```

**Keyword Scaffolding (depth 7+):**

At research depth 7+, Voku doesn't just connect nodes directly — Voku creates intermediate keyword nodes that enable future connections:

```
[new leaf: pullups-vs-lat-pulldowns]
        │
        ├── direct edge to existing node (depth 3-5)
        │
        └── at depth 7+, Voku also creates:
                [keyword: vertical-pull] ──→ [keyword: compound-movement] ──→ [fitness]
                        │
                        └── future "chin-ups" node auto-connects here
```

These keyword nodes live in Organization Space with `type='keyword'`. They're Voku's scaffolding for future connections — not shown to user by default but inspectable.

### 2.3 Bi-Temporal Model

Every belief has two time dimensions:

- **valid_from / valid_to**: When you believed this (event time)
- **recorded_at**: When Voku learned it (system time)

This enables:
- Point-in-time queries: "What did I believe about X on date Y?"
- Evolution tracking: "How has my thinking about X changed?"
- Contradiction detection: "You said A, but previously believed B"

### 2.4 Multi-Aspect Embeddings

> **⏸️ DEFERRED (Feb 06):** Start with single bge-base-en-v1.5 embedding per node. Documented retrieval problems are about Claude not reading the right files and creating duplicates — not about semantic similarity returning wrong results. Single embedding likely sufficient for dedup + connection discovery. Add additional aspects only where single embedding measurably fails during vertical slice testing. 4x storage/compute cost is unjustified without evidence.

Single embeddings only capture content semantics. Each node has multiple embeddings:

| Embedding | Purpose | Weight in Retrieval |
|-----------|---------|---------------------|
| content_embedding | Literal meaning of text | 0.3 |
| title_embedding | Semantic boundary | 0.2 |
| context_embedding | Node + parent summaries | 0.2 |
| query_embedding | "Questions this node answers" | 0.3 |

**Query embedding generation:**
```
"Given this belief: {content}
Generate 3-5 questions someone might ask where this would be a relevant answer."
```

This enables retrieval for "What guides my decisions?" to find nodes about decision principles even if "decisions" isn't in the text.

---

## 3. User Experience

### 3.1 Primary Interface: Chat + Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ┌─────────────────┐  ┌───────────────────────────────────────────┐ │
│  │                 │  │                                           │ │
│  │  CHAT (1/3)     │  │  GRAPH VIEW (2/3)                         │ │
│  │                 │  │                                           │ │
│  │  Conversation   │  │  ┌─────────┐                              │ │
│  │  with Voku     │  │  │ fitness │ (root)                       │ │
│  │                 │  │  └────┬────┘                              │ │
│  │  Research       │  │       │                                   │ │
│  │  Depth: [====5] │  │  ┌────┴────┐                              │ │
│  │                 │  │  │internal │                              │ │
│  │                 │  │  └────┬────┘                              │ │
│  │                 │  │       │                                   │ │
│  │                 │  │  ┌────┴────┐    (ghost node)              │ │
│  │                 │  │  │  leaf   │───→  40% opacity             │ │
│  │                 │  │  └─────────┘                              │ │
│  │                 │  │                                           │ │
│  └─────────────────┘  └───────────────────────────────────────────┘ │
│                                                                      │
│  [Evolution View]  [Organization Space]  [Import Documents]          │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Ghost Node Behavior

Ghosts never delete — graduated visibility with permanent searchability.

| Status | Opacity | Age | Behavior |
|--------|---------|-----|----------|
| suggested | 40% | 0-3 days | Prominent, awaiting confirmation |
| faded | 20% | 3-14 days | Visible but de-emphasized |
| archived | 0% (hidden) | 14+ days | Hidden from default view, searchable, connectable |
| rejected | 0% (hidden) | User rejected | Hidden, kept for learning, not suggested again |

**Visibility formula:**
```python
visibility = base_confidence * (0.9 ** days_since_suggested)
# Show if visibility > 0.3
# Archive if visibility < 0.1 for 3+ days
```

### 3.3 Evolution View

Primary visualization of belief change over time.

```
Timeline View:
──────────────────────────────────────────────────────────────────►
     │                    │                         │
     ▼                    ▼                         ▼
┌─────────┐         ┌─────────┐              ┌─────────┐
│Belief v1│────────►│Belief v2│─────────────►│Belief v3│
│ Jan 15  │         │ Jan 22  │              │ Jan 30  │
│         │  contradicts      │              │(current)│
└─────────┘         └─────────┘              └─────────┘

Diff View:
v1: "Lat pulldowns are effective for back development"
v2: "Compound movements are superior to isolation"
v3: "Transfer-to-function principle guides exercise choice"

Voku's Analysis:
"Your thinking progressed from exercise-specific to principle-based
reasoning over 2 weeks. The trigger appears to be your conversation
about functional training on Jan 20."
```

### 3.4 Module Declaration

Modules are user-declared focus areas representing identity and intention.

```
Current Modules:
├── fitness      (active, depth: 6) — Physical capability, training
├── career       (active, depth: 8) — Professional development, job search
├── academics    (active, depth: 5) — Courses, learning goals
├── finance      (active, depth: 3) — Portfolio, spending, runway
└── voku        (active, depth: 7) — This tool, meta-cognition
```

**Module creation:** Voku proposes when clusters form, user confirms. High bar: 3-7 modules lifetime.

---

## 4. System Capabilities

### 4.1 Store: Conversation → Nodes

**Persist criteria:**
- Facts about user (preferences, history, relationships)
- Beliefs and claims with rationale
- Decisions and their reasoning
- Goals and progress markers
- Insights and realizations

**Do not persist:**
- Conversational filler ("let's move on")
- Generic knowledge ("the sky is blue")
- Voku's own statements
- Speculative statements without commitment
- Duplicates (cosine > 0.95)

**Node Naming Convention:**

Leaf nodes must be self-documenting and atomic. Pattern: `[domain-]action-object-context[-timestamp]`

```
✅ Good (self-explanatory):
- 5k-run-session-2SECONDSmin-negative-split-2026-01-28
- observation-morning-runs-improve-focus
- decided-move-training-anchor-5pm-to-6pm
- finished-reading-thinking-fast-slow-2026-01-28

❌ Bad (loses context):
- session (what domain? what happened?)
- thinking-fast-slow (what about it? when?)
- idea (too vague)
```

Compression happens later in Organization Space — Voku creates reference nodes after patterns emerge.

**Extraction Granularity:**

Typical ratio: **1 message → 2-4 nodes** (variable, not per-sentence)

```
User message:
"Did a 5K run today, 24:30. Used negative splits—really helped 
me finish strong. I think starting too fast burns me out, but 
pacing with the first mile slow fixed it. Felt great."

Voku extracts 4 nodes:
1. [5k-run-session-2430-split-2026-01-28] (session)
2. [observation-negative-splits-improve-finish] (technique)
3. [observation-starting-fast-causes-burnout] (pattern)
4. [pacing-strategy-slow-first-mile] (relationship)

NOT extracted (stays in conversation log):
- "felt great" (captured in session notes, not standalone concept)
- "I think" (hedge word, not extractable)
- "today" (temporal marker, not concept)
```

**Extraction heuristic:**
- Extract as node: Claims, observations, sessions, decisions, concepts
- Keep in conversation: Hedges, context, feelings, conversational flow

**Extraction pipeline:**
```
Conversation Turn
       │
       ▼
┌──────────────────┐
│ STAGE 1: TRIAGE  │  Heuristics, no LLM (< 100ms)
│ - Length check   │  
│ - Belief signals │
│ - Question filter│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ STAGE 2: EMBED   │  Local model (< 200ms)
│ - Quick similar  │  
│ - Duplicate check│
└────────┬─────────┘
         │
         ▼ (async from here)
┌──────────────────┐
│ STAGE 3: EXTRACT │  LLM proposition extraction (2-4s)
│ - Decompose      │  
│ - Decontextualize│
│ - Confidence     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ STAGE 4: CONNECT │  LLM reasoning (2-3s)
│ - Find similar   │  
│ - Classify edges │
│ - Keyword links  │  (at depth 6+)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ STAGE 5: UPDATE  │  Graph write + WebSocket push
│ - Create ghosts  │  
│ - Notify UI      │
└──────────────────┘
```

**User-perceived latency: 0ms** (async processing after Stage 2)

### 4.2 Compress: Nodes → Abstractions

**Trigger criteria (at depth 6+):**
- 3+ nodes with mutual cosine similarity > 0.7
- Edge density within cluster > 0.5
- No existing internal node covers them
- Abstraction would be reusable

**Abstraction naming:**
- 2-5 words, noun phrase
- Concept-oriented, not instance-oriented
- Understandable without children context
- Example: "transfer-to-function-principle" not "notes-about-movements"

### 4.3 Extract: Query → Answer

**Module-anchored retrieval:**
```python
def retrieve(query: str, active_modules: list[str], top_k: int = 10):
    query_vec = embed(query)
    intent = classify_intent(query)  # 'global' or 'local'
    
    results_per_module = {}
    k_per_module = top_k // len(active_modules) + 1
    
    for module in active_modules:
        if intent == 'global':
            results_per_module[module] = get_module_summary(module, k_per_module)
        else:
            module_nodes = get_nodes_under_module(module)
            results_per_module[module] = multi_aspect_search(
                query_vec, module_nodes, k=k_per_module
            )
    
    # Merge with adjustments
    all_results = merge_results(results_per_module)
    for result in all_results:
        result.score *= recency_weight(result.node.updated_at)
        result.score /= math.log(result.node.degree + 1)  # Anti rich-get-richer
    
    return expand_with_context(sorted(all_results)[:top_k])
```

### 4.4 Document Import

First-class feature solving cold start.

**Supported sources:**
- PDF (papers, books)
- Markdown (notes, docs)
- Obsidian vault (preserves existing links)
- Conversation exports (LLM chat logs)

**Import flow:**
```
Document → Parse → Chunk (~300 tokens) → Extract propositions
    → Create leaves (source='import') → Find connections
    → Cluster detection → Module proposal dialog
```

**Obsidian special case:** Preserve wikilinks as edges, run connection finding for new links Voku identifies.

---

## 5. Architecture

### 5.1 System Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                    │
│  ┌───────────────┐  ┌─────────────────────────┐  ┌──────────────────┐  │
│  │ Chat (1/3)    │  │ Graph View (2/3)        │  │ Evolution View   │  │
│  │               │  │                         │  │                  │  │
│  │ Conversation  │  │ React Flow + Ghosts     │  │ Belief timeline  │  │
│  │ Depth slider  │  │ Module anchors          │  │ Diff view        │  │
│  │ Import button │  │ Organization toggle     │  │ Change triggers  │  │
│  └───────────────┘  └─────────────────────────┘  └──────────────────┘  │
│                                                                          │
│  WebSocket: Real-time bidirectional graph updates                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            BACKEND (FastAPI)                             │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    PROCESSING PIPELINE                           │    │
│  │  Triage → Embed → Extract → Connect → Update                     │    │
│  │  (fully traced, research depth affects every stage)              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Extraction  │  │ Graph       │  │ Retrieval   │  │ Evolution   │    │
│  │ Service     │  │ Service     │  │ Service     │  │ Service     │    │
│  │             │  │             │  │             │  │             │    │
│  │ Proposition │  │ Kuzu CRUD   │  │ Multi-aspect│  │ Temporal    │    │
│  │ decompose   │  │ Cypher      │  │ retrieval   │  │ queries     │    │
│  │ Decontext   │  │ Community   │  │ Module-     │  │ Contra-     │    │
│  │ Multi-embed │  │ detection   │  │ anchored    │  │ diction     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                                          │
│  ┌───────────────────────────────┐  ┌───────────────────────────────┐  │
│  │ Import Service                │  │ Organization Service          │  │
│  │                               │  │                               │  │
│  │ PDF/MD/Vault parsing          │  │ Compression, Priority,        │  │
│  │ Chunk + extract               │  │ Pattern, Hypothesis,          │  │
│  │ Module discovery              │  │ Keyword hierarchy             │  │
│  └───────────────────────────────┘  └───────────────────────────────┘  │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    PROVIDER ABSTRACTION                          │    │
│  │  Groq (fast, default) ←→ Ollama (private mode) ←→ OpenAI (opt)  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              STORAGE                                     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      voku.kuzu (Graph DB)                       │    │
│  │                                                                   │    │
│  │  User Space:                   Organization Space:               │    │
│  │  ├── ModuleNode                 ├── CompressionNode               │    │
│  │  ├── InternalNode              ├── PriorityNode                  │    │
│  │  ├── LeafNode                  ├── PatternNode                   │    │
│  │  └── GhostNode                 ├── HypothesisNode                │    │
│  │                                ├── KeywordNode                   │    │
│  │                                └── BridgeNode                    │    │
│  │                                                                   │    │
│  │  Edges: SUPPORTS, CONTRADICTS, ENABLES, CONTAINS,                │    │
│  │         SUPERSEDES, REFERENCES, SIMILAR_TO                       │    │
│  │                                                                   │    │
│  │  All nodes: bi-temporal, multi-aspect embeddings, confidence     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Auxiliary Storage (SQLite)                    │    │
│  │  - conversations (full logs + FTS5 search)                       │    │
│  │  - processing_traces (observability)                             │    │
│  │  - user_settings (depth preferences, privacy mode)               │    │
│  │  - v0.2 tables (transactions, merchants — existing)              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Graph Database | **Kuzu** | Native Cypher, community detection, path algorithms, embedded |
| Vector Index | Kuzu native | Unified storage, no sync overhead |
| Auxiliary Storage | SQLite + FTS5 | Conversations, traces, settings with full-text search |
| Frontend Graph | React Flow | Best React-native graph library |
| LLM (default) | Groq | Fast, free tier sufficient |
| LLM (private) | Ollama | Local, no data leaves machine |
| Embeddings | bge-base-en-v1.5 | 768 dim, strong retrieval benchmarks |
| WebSocket | FastAPI native | Bidirectional real-time updates |

---

## 6. Data Model (Kuzu Schema)

### 6.1 Node Tables

```cypher
// User Space Nodes
CREATE NODE TABLE ModuleNode (
    id STRING,
    title STRING,
    content STRING,
    intentions STRING,      // JSON: {primary, secondary[], definition_of_done, declared_priority}
    priority INT64,
    research_depth INT64 DEFAULT 5,
    active BOOLEAN DEFAULT true,
    declared_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
)

/* intentions JSON structure:
{
  "primary": "Run a half marathon under 2 hours",
  "secondary": ["Consistent 4x/week training", "Improve pacing strategy"],
  "definition_of_done": "Official race finish under 2:00:00",
  "declared_priority": "high"  // high | medium | low
}
*/

CREATE NODE TABLE InternalNode (
    id STRING,
    title STRING,
    content STRING,
    status STRING DEFAULT 'confirmed',  // confirmed, suggested, faded, rejected
    source STRING,                       // conversation, voku, user, import
    confidence FLOAT DEFAULT 1.0,
    node_purpose STRING,                 // observation, pattern, belief, intention, decision
    source_type STRING,                  // explicit (user stated), inferred (Voku detected)
    signal_valence STRING,               // positive, negative, neutral (relative to module intention)
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    recorded_at TIMESTAMP,
    suggested_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
)

CREATE NODE TABLE LeafNode (
    id STRING,
    title STRING,
    content STRING,
    status STRING DEFAULT 'confirmed',
    source STRING,
    confidence FLOAT DEFAULT 1.0,
    node_purpose STRING,                 // observation, pattern, belief, intention, decision
    source_type STRING,                  // explicit (user stated), inferred (Voku detected)
    signal_valence STRING,               // positive, negative, neutral (relative to module intention)
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    recorded_at TIMESTAMP,
    suggested_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
)

// Organization Space Nodes
CREATE NODE TABLE OrganizationNode (
    id STRING,
    type STRING,  // compression, priority, pattern, hypothesis, keyword, bridge
    title STRING,
    content STRING,
    confidence FLOAT,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    created_at TIMESTAMP,
    PRIMARY KEY (id)
)
```

#### Goal-Anchored Field Semantics

The `node_purpose`, `source_type`, and `signal_valence` fields enable Voku's core function: surfacing discrepancies between stated intentions and observed patterns.

**node_purpose** — What type of knowledge this represents:

| Value | Description | Example |
|-------|-------------|---------|
| `observation` | What happened (factual record) | "Ran 5K in 24:30 on Jan 28" |
| `pattern` | Recurring tendency detected | "I underestimate time for social tasks" |
| `belief` | Conviction about self/world | "Networking feels inauthentic" |
| `intention` | Stated want or goal | "I want to work at a top tech company" |
| `decision` | Choice made with rationale | "Chose Kuzu over SQLite for native graph" |

**source_type** — How this entered the system:

| Value | Description | Example |
|-------|-------------|---------|
| `explicit` | User stated directly | "I want to run a half marathon under 2 hours" |
| `inferred` | Voku detected from patterns | "You've spent 40 hours on side projects, 0 on interview prep" |

**signal_valence** — Relationship to module intention:

| Value | Description |
|-------|-------------|
| `positive` | Suggests progress toward intention |
| `negative` | Suggests regression or obstacle |
| `neutral` | Informational, no clear valence |

**Key queries these fields enable:**

```cypher
// What do I say I want?
MATCH (n) WHERE n.node_purpose = 'intention' AND n.source_type = 'explicit'

// What does my behavior suggest I want?
MATCH (n) WHERE n.node_purpose = 'pattern' AND n.source_type = 'inferred'

// What's working toward my fitness goal?
MATCH (m:ModuleNode {title: 'fitness'})-[:CONTAINS*]->(n)
WHERE n.signal_valence = 'positive'

// Where might I be deceiving myself? (stated vs revealed)
MATCH (stated) WHERE stated.node_purpose = 'intention' AND stated.source_type = 'explicit'
MATCH (revealed) WHERE revealed.node_purpose = 'pattern' AND revealed.source_type = 'inferred'
// Compare for contradictions
```

### 6.2 Edge Tables

```cypher
// User Space Edges
CREATE REL TABLE CONTAINS (
    FROM ModuleNode | InternalNode TO InternalNode | LeafNode,
    status STRING DEFAULT 'confirmed',
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP
)

CREATE REL TABLE SUPPORTS (
    FROM LeafNode | InternalNode TO LeafNode | InternalNode,
    status STRING DEFAULT 'confirmed',
    confidence FLOAT DEFAULT 1.0,
    rationale STRING,
    created_at TIMESTAMP
)

CREATE REL TABLE CONTRADICTS (
    FROM LeafNode | InternalNode TO LeafNode | InternalNode,
    status STRING DEFAULT 'confirmed',
    confidence FLOAT DEFAULT 1.0,
    rationale STRING,
    created_at TIMESTAMP
)

CREATE REL TABLE ENABLES (
    FROM LeafNode | InternalNode TO LeafNode | InternalNode,
    status STRING DEFAULT 'confirmed',
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP
)

CREATE REL TABLE SUPERSEDES (
    FROM LeafNode | InternalNode TO LeafNode | InternalNode,
    // Temporal: new belief replaces old
    created_at TIMESTAMP
)

// Cross-space Edges
CREATE REL TABLE REFERENCES (
    FROM OrganizationNode TO ModuleNode | InternalNode | LeafNode,
    created_at TIMESTAMP
)

CREATE REL TABLE SYNTHESIZES (
    FROM OrganizationNode TO OrganizationNode,
    created_at TIMESTAMP
)
```

### 6.3 Embedding Storage

```cypher
CREATE NODE TABLE NodeEmbedding (
    node_id STRING,
    embedding_type STRING,  // content, title, context, query
    embedding FLOAT[768],
    model STRING,
    created_at TIMESTAMP,
    PRIMARY KEY (node_id, embedding_type)
)
```

### 6.4 Auxiliary Tables (SQLite)

```sql
-- Conversation logs with full-text search
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    title TEXT,
    summary TEXT,
    module_ids TEXT  -- JSON array
);

CREATE TABLE conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE VIRTUAL TABLE conversation_fts USING fts5(
    content,
    content='conversation_turns',
    content_rowid='id'
);

-- Provenance linking
CREATE TABLE node_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    conversation_id TEXT,
    turn_number INTEGER,
    exact_quote TEXT,
    extraction_confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full processing observability
CREATE TABLE processing_traces (
    trace_id TEXT PRIMARY KEY,
    conversation_id TEXT,
    turn_number INTEGER,
    input_content TEXT,
    research_depth INTEGER,
    triage_result JSON,
    extraction_result JSON,
    embedding_result JSON,
    connection_result JSON,
    triage_latency_ms INTEGER,
    extraction_latency_ms INTEGER,
    embedding_latency_ms INTEGER,
    connection_latency_ms INTEGER,
    total_latency_ms INTEGER,
    nodes_created INTEGER,
    edges_created INTEGER,
    provider_used TEXT,
    errors JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences
CREATE TABLE user_settings (
    key TEXT PRIMARY KEY,
    value TEXT  -- JSON for complex values
);

CREATE TABLE processing_config (
    scope TEXT,  -- 'global', 'module:{id}', 'session:{id}'
    depth INTEGER,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    PRIMARY KEY (scope, valid_from)
);
```

---

## 7. Intelligence Operations

### 7.1 Proposition Extraction Prompt

```
Given this conversation turn from the user:
"{turn_content}"

Context from recent conversation:
"{recent_context}"

Research depth: {depth} (0=minimal, 10=maximum extraction)

Extract atomic propositions. Each proposition should:
- Be self-contained (understandable without context)
- Replace pronouns with explicit references ("he" → "User")
- Contain ONE claim, fact, preference, or insight
- Be 20-80 words

Return JSON:
{
  "propositions": [
    {
      "content": "...",
      "title": "descriptive-kebab-case-title",
      "type": "fact|belief|preference|goal|insight|decision",
      "confidence": 0.0-1.0,
      "temporal_marker": "ongoing|point-in-time|null"
    }
  ],
  "store_decision": true|false,
  "skip_reason": "..." // if not storing
}
```

### 7.2 Connection Finding Prompt

```
Given this new node:
Title: "{node_title}"
Content: "{node_content}"
Module: "{parent_module}"

And these potentially related existing nodes:
{similar_nodes_json}

Research depth: {depth}

For each existing node, determine:
1. Is there a meaningful relationship?
2. What type? (supports, contradicts, enables, references)
3. Confidence (0.0-1.0)
4. Brief rationale

At depth 6+, also identify:
- Keyword hierarchy this node should connect to
- Potential cross-module bridges

Return JSON:
{
  "proposed_edges": [
    {
      "to_node_id": "...",
      "relationship": "...",
      "confidence": 0.0,
      "rationale": "..."
    }
  ],
  "keyword_chain": ["specific", "general", "more_general"],  // depth 6+
  "cross_module_bridges": [...]  // depth 6+
}
```

### 7.3 Query Embedding Generation Prompt

```
Given this belief/insight:
"{node_content}"

Generate 3-5 questions that someone might ask where this would be a relevant answer.
Focus on questions that use different vocabulary than the content itself.

Return JSON:
{
  "questions": [
    "What guides my exercise selection?",
    "Why do I prefer certain movements?",
    ...
  ]
}
```

### 7.4 Belief Evolution Detection

```python
def detect_belief_evolution(new_node, existing_nodes):
    for existing in find_similar(new_node, threshold=0.7):
        evolution_type = classify_evolution(new_node, existing)
        
        if evolution_type == 'contradiction':
            # Clear change of mind
            create_edge(new_node, existing, 'SUPERSEDES')
            existing.valid_to = now()
            new_node.valid_from = now()
            
            # Surface to user at depth 7+
            if research_depth >= 7:
                notify_evolution(existing, new_node, 'contradiction')
        
        elif evolution_type == 'refinement':
            # Same direction, more nuanced
            create_edge(new_node, existing, 'SUPPORTS')
            # Don't invalidate, both remain valid
        
        elif evolution_type == 'extension':
            create_edge(new_node, existing, 'ENABLES')
```

---

## 8. Interview Narrative

### Core Story (30 seconds)
"Voku is a knowledge-first cognitive prosthetic. You talk to it naturally, and it extracts your beliefs into a graph — watch it build as we speak. The key innovations are: research depth as an architectural axis affecting every operation, a hidden organization layer where Voku reasons before proposing, and belief evolution tracking that shows how your thinking changes over time. It's not another chatbot; it's your externalized mental model."

### Technical Deep Dives

**"Why Kuzu over SQLite?"**
"Graph traversal is central to Voku — finding paths between concepts, detecting communities for abstraction, measuring centrality for importance. SQLite recursive CTEs work but don't express graph semantics. Kuzu gives me native Cypher, built-in community detection, and path algorithms. For engineering roles, fluency with graph data structures is directly relevant."

**"How does multi-aspect embedding work?"**
"Single embeddings only capture content semantics. I generate four embeddings per node: content, title, context with parent summaries, and hypothetical queries this node answers. The query embedding is key — 'What guides my decisions?' matches nodes about decision principles even if 'decisions' isn't in the text. This is similar to HyDE but applied at indexing time."

**"What's the organization layer?"**
"Voku needs working memory — pattern detection, hypothesis formation, priority computation — that shouldn't clutter the user's graph. Organization space holds compression nodes, keyword hierarchies, and cross-domain bridges. It's inspectable: users can ask 'why did you suggest this?' and see Voku's reasoning chain. This separation lets Voku think without polluting the user's mental model."

**"How do you handle belief evolution?"**
"Bi-temporal model: valid_from/valid_to tracks when beliefs were true, recorded_at tracks when Voku learned them. When a new node contradicts an existing one with high similarity, Voku creates a SUPERSEDES edge, closes the old belief's validity window, and at research depth 7+ surfaces the evolution to the user. You can query 'What did I believe about X on date Y?' or see your thinking evolve on a timeline."

**"Why research depth as an axis?"**
"It's not a feature toggle — every operation behaves differently. Depth 3 does quick extraction and obvious connections. Depth 7 builds keyword hierarchies and detects cross-module bridges. Depth 10 generates hypotheses and finds gaps in your thinking. This lets users choose between quick capture and deep synthesis without building two separate systems."

---

## 9. Files Reference

| File | Purpose |
|------|---------|
| `docs/DESIGN_V03.md` | This document — complete architecture |
| `docs/ARCHITECTURE_DIAGRAMS.md` | Mermaid visual diagrams |
| `docs/STATE.md` | Implementation status tracker |
| `docs/API.md` | REST endpoint documentation |
| `backend/app/services/graph/` | Kuzu graph operations |
| `backend/app/services/extraction/` | Proposition extraction pipeline |
| `backend/app/services/retrieval/` | Multi-aspect retrieval |
| `backend/app/services/evolution/` | Temporal queries, contradiction detection |
| `backend/app/services/organization/` | Voku's cognitive workspace |
| `backend/app/services/import_/` | Document import pipeline |

---

## 10. Next Steps

Implementation begins with graph foundation:
1. Kuzu schema setup + basic CRUD
2. Processing pipeline with observability
3. Multi-aspect embedding generation
4. Module bootstrap + document import
5. Chat + Graph UI with WebSocket
6. Retrieval + Evolution features
7. Organization layer operations

See STATE.md for current progress.
