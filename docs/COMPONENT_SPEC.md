# Voku Component Specification

**Created:** 2026-02-11
**Derives from:** `CONSTRAINTS.md` — every component traces to a constraint.
**Status:** Living document. Updated as spikes resolve unknowns.

---

## Overview

Voku is a personal context engine that ingests conversations, extracts propositions, tracks belief evolution, and serves temporally-aware context. This spec defines every component needed for the March 31 demo, organized by milestone.

### What Exists (from Phase 0-1, still valid)
- `services/extraction/` — LLM proposition extraction with 5-layer validation ✅
- `services/embeddings.py` — bge-base-en-v1.5, 768-dim vectors ✅ (interface swap needed)
- `services/providers/` — Groq + Ollama abstraction ✅
- `services/chat.py` — Pipeline orchestration (needs rewiring to SQLite)
- `services/graph/` — Kuzu operations (DEPRECATED — being replaced by SQLite)

### What Gets Built (this spec)
- Milestone 1: Storage layer, batch import parser, embedding interface
- Milestone 2: Golden test set, evaluation harness
- Milestone 3: Process mode, temporal retrieval
- Milestone 4: MCP server, visualization

---

## Milestone 1: Ingest Real Data

**Goal:** Import 5+ real Claude conversations → extract propositions → store in SQLite with embeddings → retrieve by similarity. End-to-end vertical slice.
**Constraint:** Tier 0.2 (real data), Tier 2.9 (vertical slice), Tier 2.8 (spike first)
**Gate:** `pytest tests/test_milestone1.py -v` passes.

---

### Component 1.1: Conversation Import Parser

**Purpose:** Parse Claude.ai conversation exports (markdown) into structured messages.

**Input:**
```
## 2026-02-10T22:15:00Z - Jaymin

I think my main limiter for rowing is my ankle — I can't get full extension.

## 2026-02-10T22:15:30Z - Claude

That's a common issue with...
```

**Output:**
```python
@dataclass
class ConversationMessage:
    text: str              # Raw message text
    speaker: str           # "user" or "assistant"
    timestamp: datetime    # Parsed from header
    session_id: str        # Derived from filename or first timestamp
    message_index: int     # Order within conversation
```

**Interface:**
```python
class ConversationParser:
    def parse_file(self, filepath: Path) -> list[ConversationMessage]:
        """Parse a single exported conversation file."""
        ...

    def parse_directory(self, dirpath: Path) -> list[ConversationMessage]:
        """Parse all .md files in a directory."""
        ...
```

**Edge cases to handle:**
- Empty messages (skip)
- Messages with images/attachments (extract text, note attachment)
- Malformed timestamps (log warning, use previous timestamp + 1s)
- Multi-paragraph messages (preserve as single message)
- Assistant messages (store but flag — extraction targets user messages only)

**Dependencies:** None (pure parsing, no external services)

**Tests needed:**
- Parse single well-formed conversation → correct message count, timestamps, speakers
- Parse conversation with malformed timestamp → graceful fallback
- Parse conversation with empty messages → skipped
- Parse directory of 5 conversations → all messages extracted
- Roundtrip: known input file → exact expected output

**Spike needed:** YES — export 3 conversations from claude.ai, examine actual format before finalizing parser. Format may differ from assumed `## timestamp - speaker` pattern.

---

### Component 1.2: SQLite Storage Layer

**Purpose:** Store propositions, embeddings, and metadata in a single SQLite file. Replaces Kuzu for user space.

**Schema:**
```sql
-- User space (immutable after write)
CREATE TABLE propositions (
    id TEXT PRIMARY KEY,           -- UUID
    text TEXT NOT NULL,             -- Original proposition text
    node_type TEXT NOT NULL,        -- BELIEF/GOAL/OBSERVATION/DECISION/PATTERN/LEARNING/EMOTIONAL
    confidence TEXT DEFAULT 'MEDIUM', -- HIGH/MEDIUM/LOW
    source_type TEXT DEFAULT 'conversation',
    created_at TEXT NOT NULL,       -- ISO 8601
    session_id TEXT,                -- Links to source conversation
    message_id TEXT,                -- Links to specific message
    domain_tags TEXT DEFAULT '[]',  -- JSON array
    status TEXT DEFAULT 'ACTIVE'    -- ACTIVE/SUPERSEDED/CONTRADICTED
);

-- Embeddings (separate table per SQLite BLOB best practice)
CREATE TABLE embeddings (
    proposition_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,        -- numpy float32 array as bytes
    model TEXT NOT NULL,             -- e.g. 'bge-base-en-v1.5' or 'embeddinggemma-300m'
    dimensions INTEGER NOT NULL,    -- 768
    FOREIGN KEY (proposition_id) REFERENCES propositions(id)
);

-- Org space (rebuilt by process layer — Milestone 3)
CREATE TABLE edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,         -- SUPPORTS/CONTRADICTS/SUPERSEDES/DERIVED_FROM
    confidence REAL,
    created_at TEXT NOT NULL,
    created_by TEXT DEFAULT 'process_v1',
    FOREIGN KEY (source_id) REFERENCES propositions(id),
    FOREIGN KEY (target_id) REFERENCES propositions(id)
);

CREATE TABLE thread_surfaces (
    id TEXT PRIMARY KEY,
    domain_cluster TEXT,
    summary_text TEXT NOT NULL,
    confidence REAL,
    supporting_node_ids TEXT NOT NULL, -- JSON array of proposition IDs
    last_updated TEXT NOT NULL
);
```

**SQLite Configuration:**
```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;
PRAGMA cache_size=-64000;
```

**Interface:**
```python
class StorageService(ABC):
    """Abstract storage interface — implementations are swappable (Constraint 3.13)."""

    @abstractmethod
    def store_proposition(self, proposition: StoredProposition) -> str: ...

    @abstractmethod
    def store_embedding(self, proposition_id: str, embedding: np.ndarray, model: str) -> None: ...

    @abstractmethod
    def find_similar(self, embedding: np.ndarray, threshold: float = 0.85, limit: int = 10) -> list[SimilarResult]: ...

    @abstractmethod
    def find_by_timerange(self, start: datetime, end: datetime) -> list[StoredProposition]: ...

    @abstractmethod
    def find_by_session(self, session_id: str) -> list[StoredProposition]: ...

    @abstractmethod
    def get_all_embeddings(self) -> tuple[list[str], np.ndarray]: ...
        """Load all embeddings into memory for numpy operations. Returns (ids, embedding_matrix)."""


class SQLiteStorage(StorageService):
    """SQLite implementation. Single file, numpy for vector search."""
    ...
```

**Vector search strategy (Constraint 3.14 — minimum viable complexity):**
- On startup: load all embeddings into memory as numpy matrix
- Cosine similarity via `numpy.dot` + norms (pre-computed)
- At 50K propositions × 768 dims: ~150MB memory, <15ms search
- Cache invalidated on new writes (append new row to in-memory matrix)
- No sqlite-vec dependency (maintenance risk identified in tech review)

**Tests needed:**
- Store and retrieve single proposition → data matches
- Store embedding, find by similarity → correct match above threshold
- Find by timerange → correct temporal filtering
- Find by session → correct grouping
- Dedup: store duplicate embedding → find_similar returns existing
- Load all embeddings → correct matrix shape
- Database file is single .db file, portable (copy + open in new location works)

**Dependencies:** sqlite3 (stdlib), numpy

---

### Component 1.3: Embedding Interface

**Purpose:** Abstract interface for embedding models. Allows swapping bge-base → EmbeddingGemma without touching calling code. (Constraint 3.13)

**Interface:**
```python
class EmbeddingProvider(ABC):
    """Abstract embedding interface."""

    @abstractmethod
    def embed(self, text: str) -> np.ndarray: ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> np.ndarray: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...


class BGEBaseEmbedding(EmbeddingProvider):
    """Current: sentence-transformers bge-base-en-v1.5, 768 dims."""
    ...

class OllamaEmbedding(EmbeddingProvider):
    """Future: EmbeddingGemma or nomic-embed via Ollama API, 768 dims."""
    ...
```

**Tests needed:**
- BGE embed single text → 768-dim array
- BGE embed batch → correct shape (N × 768)
- Two implementations produce same-dimension output
- Cosine similarity of related texts > 0.7
- Cosine similarity of unrelated texts < 0.5

**Spike needed:** YES — compare bge-base vs EmbeddingGemma on 20 real Voku propositions. Measure retrieval quality (do the right propositions surface for test queries?). Decision: switch only if EmbeddingGemma is measurably better on our data.

---

### Component 1.4: Ingestion Pipeline (rewired ChatService)

**Purpose:** Orchestrate the flow: conversation messages → extraction → embedding → dedup → store. Replaces current ChatService's Kuzu dependency with SQLite.

**Interface:**
```python
class IngestionService:
    """Orchestrates import → extract → embed → dedup → store."""

    def __init__(
        self,
        storage: StorageService,
        extraction: ExtractionService,
        embedder: EmbeddingProvider,
        provider: Provider,
    ): ...

    async def ingest_message(self, message: ConversationMessage) -> IngestionResult: ...
        """Process single message: extract → embed → dedup → store."""

    async def ingest_conversation(self, messages: list[ConversationMessage]) -> BatchIngestionResult: ...
        """Process full conversation. User messages only."""

    async def ingest_directory(self, dirpath: Path) -> BatchIngestionResult: ...
        """Parse and ingest all conversations in a directory."""
```

**Output:**
```python
@dataclass
class IngestionResult:
    propositions_extracted: int
    propositions_stored: int       # After dedup
    duplicates_found: int
    session_id: str

@dataclass
class BatchIngestionResult:
    total_messages: int
    total_propositions_extracted: int
    total_propositions_stored: int
    total_duplicates: int
    sessions_processed: int
    errors: list[str]              # Non-fatal errors (malformed messages, etc.)
```

**Flow:**
1. Filter to user messages only (assistant messages stored as raw context, not extracted)
2. For each user message: call ExtractionService.extract()
3. For each proposition: call EmbeddingProvider.embed()
4. For each (proposition, embedding): check StorageService.find_similar(threshold=0.95)
5. If no duplicate: StorageService.store_proposition() + store_embedding()
6. Return counts

**Tests needed:**
- Ingest single message → propositions stored in SQLite
- Ingest message with duplicate proposition → dedup fires, count correct
- Ingest full conversation (5+ messages) → all user messages processed, assistant skipped
- Ingest directory → multiple sessions processed
- Error handling: extraction fails on one message → others still processed

**Dependencies:** Components 1.1, 1.2, 1.3, plus existing ExtractionService + Provider

---

### Milestone 1 Integration Test

**The gate test.** This is the single test that proves Milestone 1 works.

```python
def test_milestone1_vertical_slice():
    """
    End-to-end: real conversation export → SQLite with propositions + embeddings.
    
    1. Parse real exported conversation file
    2. Ingest through full pipeline
    3. Query: find propositions about "rowing"
    4. Assert: relevant propositions surface, irrelevant ones don't
    5. Query: find propositions from specific session
    6. Assert: correct session grouping
    """
```

---

## Milestone 2: Prove Retrieval Works

**Goal:** Build evaluation infrastructure. Create golden test set. Run first metrics. Establish baseline.
**Constraint:** Tier 1.6 (evaluation is first-class), Tier 0.1 (must demonstrate temporal tracking)
**Gate:** Golden test set runs, baseline numbers recorded, comparison with naive retrieval complete.

---

### Component 2.1: Golden Test Set

**Purpose:** 50 test cases that define what "correct retrieval" means for Voku.

**Structure:**
```python
@dataclass
class TestCase:
    id: str
    category: str          # "basic_retrieval" | "temporal" | "contradiction" | "multi_hop"
    setup_propositions: list[dict]  # Propositions to seed (with timestamps)
    query: str                       # The retrieval query
    expected_ids: list[str]          # Which propositions SHOULD be retrieved
    expected_absent_ids: list[str]   # Which propositions should NOT be retrieved
    temporal_expected: str | None    # For temporal cases: which belief is "current"
    notes: str                       # Why this test case matters
```

**Categories:**
- **Basic retrieval (15 cases):** Clear propositions, straightforward queries. Sanity check.
- **Temporal reasoning (15 cases):** Belief evolution pairs with timestamps. The core test.
- **Contradiction handling (10 cases):** Within-session and cross-session contradictions.
- **Multi-hop reasoning (10 cases):** Queries requiring combination of multiple propositions.

**Source:** Hand-written from Jaymin's real conversation history. Not synthetic.

**File format:** JSON file (`tests/golden/test_cases.json`) loadable by evaluation harness.

---

### Component 2.2: Retrieval Service

**Purpose:** Given a query, return the most relevant propositions with temporal awareness.

**Interface:**
```python
class RetrievalService:
    """Retrieve relevant context for a query."""

    def __init__(self, storage: StorageService, embedder: EmbeddingProvider): ...

    def retrieve(
        self,
        query: str,
        limit: int = 10,
        temporal_weight: float = 0.3,  # How much to favor recent propositions
    ) -> list[RetrievalResult]: ...

    def retrieve_for_topic(
        self,
        topic: str,
        include_history: bool = True,  # Include superseded beliefs
    ) -> TopicTimeline: ...


@dataclass
class RetrievalResult:
    proposition_id: str
    text: str
    similarity: float          # Embedding cosine similarity
    recency_score: float       # Temporal weighting
    combined_score: float      # similarity * (1 - temporal_weight) + recency * temporal_weight
    created_at: datetime
    status: str                # ACTIVE/SUPERSEDED/CONTRADICTED
    session_id: str

@dataclass
class TopicTimeline:
    current_belief: RetrievalResult | None    # Most recent ACTIVE proposition
    history: list[RetrievalResult]            # Chronological evolution
    contradictions: list[tuple[RetrievalResult, RetrievalResult]]  # Detected conflicts
```

**Tests needed:**
- Basic query → returns relevant propositions ranked by similarity
- Temporal query (topic with evolved beliefs) → current belief ranked highest
- Topic timeline → chronological ordering with status flags
- Empty results → graceful empty return

---

### Component 2.3: Evaluation Harness

**Purpose:** Run golden test set against retrieval, compute metrics, compare configurations.

**Interface:**
```python
class EvaluationHarness:
    """Run evaluation suite and compute metrics."""

    def __init__(self, retrieval: RetrievalService, storage: StorageService): ...

    def run_golden_set(self, test_cases: list[TestCase]) -> EvaluationReport: ...

    def run_ablation(
        self,
        test_cases: list[TestCase],
        configs: dict[str, RetrievalService],  # Named configurations to compare
    ) -> AblationReport: ...


@dataclass
class EvaluationReport:
    hit_rate: float              # % of queries with at least one relevant result
    mrr: float                   # Mean Reciprocal Rank
    temporal_accuracy: float     # % of temporal queries returning current belief
    contradiction_detection: float  # % of contradictions correctly flagged
    per_category: dict[str, CategoryMetrics]
    per_case: list[CaseResult]   # Individual case results for debugging

@dataclass
class AblationReport:
    configs: dict[str, EvaluationReport]   # Results per configuration
    deltas: dict[str, dict[str, float]]    # Per-metric differences between configs
```

**Ablation configurations (Milestone 2 — first pass):**
1. **Full system** — embedding similarity + temporal weighting
2. **No temporal weighting** — embedding similarity only
3. **No context** — baseline (random or no retrieval)

**Tests needed:**
- Run on minimal (5-case) golden set → report computes, all fields populated
- Hit rate computation → correct math
- Temporal accuracy → correct identification of "current" belief
- Ablation → produces comparison between configs

**Dependencies:** Components 2.1, 2.2, plus Milestone 1 storage

---

## Milestone 3: Prove Temporal Tracking Works

**Goal:** Build process mode. Detect contradictions. Update belief status. Demonstrate the thesis.
**Constraint:** Tier 0.1 (THE thesis — temporal belief tracking)
**Gate:** Temporal accuracy metric improves measurably over Milestone 2 baseline. At least one real contradiction detected and resolved from Jaymin's conversation data.

---

### Component 3.1: Process Mode Engine

**Purpose:** After ingestion, replay new propositions against existing knowledge to discover relationships.

**Interface:**
```python
class ProcessEngine:
    """Discovers relationships between propositions. Runs after ingestion."""

    def __init__(
        self,
        storage: StorageService,
        retrieval: RetrievalService,
        llm: Provider,
    ): ...

    async def process_new(self, since: datetime | None = None) -> ProcessResult: ...
        """Process all propositions added since last run (or since given time)."""

    async def process_pair(self, prop_a_id: str, prop_b_id: str) -> RelationshipResult | None: ...
        """Evaluate relationship between two specific propositions."""

    async def build_thread_surfaces(self) -> list[ThreadSurface]: ...
        """Generate thread summaries from proposition clusters."""


@dataclass
class ProcessResult:
    propositions_analyzed: int
    edges_created: int
    contradictions_found: int
    supersessions_found: int
    thread_surfaces_updated: int

@dataclass
class RelationshipResult:
    edge_type: str          # SUPPORTS/CONTRADICTS/SUPERSEDES/UNRELATED
    confidence: float
    reasoning: str          # LLM's explanation (stored for debugging/provenance)
```

**Process flow:**
1. Get all propositions since last process run
2. For each new proposition: find top-K similar existing propositions (embedding search)
3. For each (new, existing) pair above similarity threshold:
   - Send to LLM: "Given these two propositions with timestamps, are they: supporting, contradicting, superseding, or unrelated?"
   - If CONTRADICTS or SUPERSEDES: create edge, update status of older proposition
4. Cluster propositions by embedding similarity → generate/update thread surfaces
5. Store all edges and thread surfaces in org space tables

**LLM prompt contract (sketch):**
```
Given two propositions from the same person at different times:

Proposition A (recorded {timestamp_a}): "{text_a}"
Proposition B (recorded {timestamp_b}): "{text_b}"

What is the relationship?
- SUPPORTS: B reinforces or adds evidence to A
- CONTRADICTS: B conflicts with A (both could be simultaneously held)
- SUPERSEDES: B replaces A (the person changed their mind)
- UNRELATED: No meaningful relationship

Respond with JSON: {"relationship": "...", "confidence": 0.0-1.0, "reasoning": "..."}
```

**Tests needed:**
- Two clearly contradicting propositions → CONTRADICTS edge created
- Two clearly supporting propositions → SUPPORTS edge created
- Supersession (later belief replaces earlier) → SUPERSEDES edge, earlier status updated
- Unrelated propositions → no edge created
- Process mode updates thread surfaces → summary reflects current state
- Real data test: process Jaymin's rowing conversations → ankle-as-limiter → breathing-as-limiter supersession detected

---

### Component 3.2: Temporal Retrieval (Enhanced)

**Purpose:** Upgrade RetrievalService to use org space edges and thread surfaces.

**Additions to Component 2.2 interface:**
```python
class TemporalRetrievalService(RetrievalService):
    """Retrieval enhanced with org space knowledge."""

    def retrieve(self, query: str, ...) -> list[RetrievalResult]:
        """Now uses: embedding similarity + temporal weight + status awareness.
        SUPERSEDED propositions are deprioritized. Thread surfaces provide context."""

    def get_belief_timeline(self, topic: str) -> BeliefTimeline: ...
        """Full evolution of beliefs on a topic, with edges showing why each change happened."""
```

**Key behavior change:** When a query matches a superseded proposition, retrieval returns the superseding proposition instead, with the history available on request.

---

### Milestone 3 Integration Test

```python
def test_temporal_tracking_thesis():
    """
    THE test. Proves Voku's reason to exist.

    1. Ingest conversations where a belief evolves
       (e.g., "ankle is main limiter" → "breathing is main limiter")
    2. Run process mode
    3. Query: "what is the user's main rowing limiter?"
    4. Assert: returns breathing, not ankle
    5. Assert: ankle proposition has status SUPERSEDED
    6. Assert: SUPERSEDES edge exists between the two
    7. Query topic timeline → shows evolution with evidence
    8. Compare: same query against flat retrieval (no process mode) → returns ankle
       (because it was mentioned first/more times)
    """
```

---

## Milestone 4: Make It Usable

**Goal:** Serve context to Claude Desktop via MCP. Optionally visualize graph.
**Constraint:** Tier 2.10 (visualization simplifies first), Tier 1.5 (March 31 target)
**Gate:** Claude Desktop receives Voku context for at least one conversation.

---

### Component 4.1: MCP Server

**Purpose:** Serve Voku context to Claude Desktop via Model Context Protocol.

**Interface (FastMCP tools):**
```python
@mcp.tool()
def get_relevant_context(query: str, limit: int = 5) -> str:
    """Retrieve relevant propositions for the current conversation."""

@mcp.tool()
def get_topic_timeline(topic: str) -> str:
    """Get the evolution of beliefs on a specific topic."""

@mcp.tool()
def get_thread_surfaces() -> str:
    """Get current thread summaries — what Voku currently understands."""
```

**Transport:** stdio (local, no auth needed for personal use)

**Tests needed:**
- Tool returns valid JSON with expected fields
- Empty database → graceful empty response
- Query with results → propositions returned with metadata

---

### Component 4.2: Visualization (FLEX — simplify if time-constrained)

**Minimum viable:** Static HTML page showing proposition nodes colored by status, clustered by embedding similarity. Clickable for detail.

**Nice to have:** React Flow interactive graph with temporal filtering, session markers, thread surface overlays.

**Decision deferred to Milestone 4 based on remaining time (Constraint 2.10).**

---

## Component Dependency Graph

```
1.1 Conversation Parser ──→ 1.4 Ingestion Pipeline
1.2 SQLite Storage ────────→ 1.4 Ingestion Pipeline ──→ 2.2 Retrieval Service
1.3 Embedding Interface ──→ 1.4 Ingestion Pipeline       ↓
                                                     2.3 Evaluation Harness
                                                          ↓
                              3.1 Process Engine ────→ 3.2 Temporal Retrieval
                                                          ↓
                              4.1 MCP Server ←───────── serves context
                              4.2 Visualization ←─────── reads from storage
```

---

## Spikes Required Before Building

| Spike | Question | Time Box | Blocks |
|-------|----------|----------|--------|
| S1: Export format | What does claude.ai markdown export actually look like? | 1 hour | Component 1.1 |
| S2: EmbeddingGemma | Is it measurably better than bge-base on our propositions? | 2 hours | Component 1.3 decision |
| S3: Extraction on real exports | Does current extraction prompt work on full conversation messages? | 2 hours | Component 1.4 quality |
| S4: LLM relationship detection | Can Groq/Ollama reliably classify SUPPORTS/CONTRADICTS/SUPERSEDES? | 2 hours | Component 3.1 feasibility |

**Spikes S1-S3 should run before Milestone 1 build. S4 can run during Milestone 2.**

---

## File Organization (Post-Migration)

```
backend/app/
├── services/
│   ├── storage/
│   │   ├── __init__.py         # StorageService ABC
│   │   └── sqlite.py           # SQLiteStorage implementation
│   ├── embedding/
│   │   ├── __init__.py         # EmbeddingProvider ABC
│   │   ├── bge.py              # BGEBaseEmbedding
│   │   └── ollama.py           # OllamaEmbedding (EmbeddingGemma)
│   ├── extraction/             # (existing, unchanged)
│   ├── providers/              # (existing, unchanged)
│   ├── retrieval.py            # RetrievalService
│   ├── process.py              # ProcessEngine
│   └── ingestion.py            # IngestionService
├── models/
│   ├── proposition.py          # StoredProposition, ConversationMessage
│   └── evaluation.py           # TestCase, EvaluationReport
├── mcp/
│   └── server.py               # FastMCP server
├── config.py                   # (existing, updated for SQLite)
├── dependencies.py             # (existing, rewritten for new services)
└── main.py                     # (existing, updated lifespan)

tests/
├── test_storage.py
├── test_embedding.py
├── test_ingestion.py
├── test_retrieval.py
├── test_process.py
├── test_evaluation.py
├── test_milestone1.py          # Integration gate
├── test_milestone3.py          # Temporal tracking gate
└── golden/
    └── test_cases.json         # 50-case golden test set
```
