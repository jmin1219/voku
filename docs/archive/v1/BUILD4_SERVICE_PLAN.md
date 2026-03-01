# Build 4 — Service Layer Plan

> Maps USERMODEL.md processes to code. Read alongside USERMODEL.md.

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   ├── user_model/
│   │   │   ├── __init__.py
│   │   │   ├── storage.py         -- UserModelStorage: CRUD for user_model + model_evidence
│   │   │   ├── assignment.py      -- AssignmentService: two-pass proposition → dimension mapping
│   │   │   ├── inference.py       -- ExhaleService: per-dimension inference, threshold gating
│   │   │   ├── emergence.py       -- EmergenceDetector: splits + uncategorized clustering
│   │   │   └── context.py         -- ContextAssemblyV2: inverse-confidence weighted system prompt
│   │   └── ... (existing services unchanged)
│   ├── routes/
│   │   ├── user_model.py      -- GET /api/model, POST /api/model/{id}/confirm
│   │   └── ... (existing routes unchanged)
│   └── migrations/
│       └── consolidate_db.py  -- One-time: merge two DBs → single voku.db
└── data/                          -- DBs (gitignored)
```

**Seed config:** `backend/app/dimension_seeds.json` (committed, generic defaults). Personal override: `backend/app/dimension_seeds.local.json` (gitignored).

## Piece 0: DB Consolidation — Concrete Steps

**Current state:**
- `backend/data/m2_conversation.db` — propositions (425 rows), embeddings (425 rows), edges (0 rows)
- `backend/data/voku.db` — conversations (15 rows), messages (31 rows)
- Stale files to ignore: m2_conv_retest.db, m2_conv_test.db, m2_v2.db, ingest_log.txt

**Target:** Single `backend/data/voku.db` with all 5 tables (propositions, embeddings, edges, conversations, messages).

**Steps:**
1. Create `backend/migrations/consolidate_db.py`:
   - Copy conversations + messages tables from old voku.db into m2_conversation.db
   - Rename m2_conversation.db → voku.db (or copy to new file)
   - Verify row counts match
2. Update `backend/app/config.py`: single `db_path = "./data/voku.db"`, remove `propositions_db_path`
3. Update `backend/app/dependencies.py`: single `SQLiteStorage(settings.db_path)`
4. Update `backend/app/routes/extract.py`: ConversationService uses same db_path
5. Update `backend/app/services/conversation/service.py` if it hardcodes a path
6. Run all 52 tests — must pass unchanged
7. Start backend + frontend, verify chat + extraction + phase space still work

**After consolidation, stale files can be moved to `backend/data/archive/`.**

---

## Seed Configuration

```json
// data/dimension_seeds.json (committed — generic defaults)
[
  {
    "id": "self",
    "dimension": "self",
    "subdimension": null,
    "description": "Identity, values, self-concept, emotional life, psychological patterns, how the person thinks, copes, regulates, and grows. Who they are when no one is watching.",
    "decay_class": "core"
  },
  {
    "id": "pursuits",
    "dimension": "pursuits",
    "subdimension": null,
    "description": "Career, projects, goals, plans, skills, creative work, learning-in-service-of-doing. What the person is building and working toward.",
    "decay_class": "preference"
  },
  {
    "id": "relationships",
    "dimension": "relationships",
    "subdimension": null,
    "description": "Connections, family, friends, romantic life, social needs, relational patterns and history. How the person relates to other people.",
    "decay_class": "preference"
  },
  {
    "id": "body",
    "dimension": "body",
    "subdimension": null,
    "description": "Health, fitness, energy, nutrition, sleep, physical state, limitations, embodied experience. What the body enables and constrains.",
    "decay_class": "situational"
  }
]
```

Seed script loads `dimension_seeds.local.json` if it exists, falls back to `dimension_seeds.json`. Personal overrides can add refined descriptions without changing committed code.

## Service Responsibilities

### `user_model/storage.py` — UserModelStorage
- `init_tables()` — CREATE TABLE IF NOT EXISTS for user_model + model_evidence
- `add_evidence_mode_column()` — ALTER TABLE propositions ADD COLUMN evidence_mode (migration)
- `seed_dimensions(config_path)` — Load JSON, insert seed rows (idempotent)
- `get_dimension(id)` → UserModelRow
- `get_all_dimensions(status='active')` → list[UserModelRow]
- `get_children(parent_id)` → list[UserModelRow] (subdimensions of a seed)
- `update_dimension(id, estimate, confidence, uncertainty_type, reasoning_trace)` — with threshold gate
- `append_history(id, old_estimate, timestamp)` — only called when gate passes
- `propose_dimension(id, dimension, subdimension, description, proposed_from, parent_id)` — insert with status='proposed'
- `confirm_dimension(id)` / `retire_dimension(id)` / `rename_dimension(id, new_description)`
- `get_evidence_for_dimension(model_id)` → list of propositions with relevance/direction/evidence_mode
- `store_assignments(assignments: list[Assignment])` — batch insert into model_evidence
- `get_unassigned_propositions()` → propositions with 0 entries in model_evidence
- Shares same DB connection as propositions_storage (after consolidation)

### `user_model/assignment.py` — AssignmentService
- `assign_batch(propositions, dimensions)` → list[Assignment]
  - Pass 1: classify each proposition to 0-3 dimensions
    - Prompt: "What does this tell you about this person?"
    - With 4 coarse seeds → trivially easy, near-zero error rate
  - Pass 2: score relevance + direction per (proposition, dimension) pair
  - Also classifies evidence_mode (experiential/retrospective) from temporal cues
- Uses provider abstraction (Groq for classification)

### `user_model/inference.py` — ExhaleService
- `exhale(dimension_id)` → ExhaleResult
  1. Gather evidence, weight by evidence_mode
  2. Get current estimate + confidence
  3. Identify active goals, compute goal adjacency
  4. LLM inference with evidence + goals + current state
  5. For retrospective evidence: note introduction context in reasoning_trace
  6. **Threshold gate:** embed old vs new, check deltas, verify citations
  7. If passes: commit update, append to summary_history
- `exhale_all()` — all dimensions with new evidence or crossed decay threshold
- `compute_entrenchment()` — cross-goal activation after per-dimension exhale

### `user_model/emergence.py` — EmergenceDetector
- `check_splits()` → list[ProposedDimension]
  - For each seed with 30+ assigned propositions
  - DBSCAN on evidence embeddings (eps=0.7, min_samples=10)
  - If 2+ clusters → propose subdimension split with auto-generated descriptions
- `check_uncategorized()` → list[ProposedDimension]
  - Get all propositions with 0 assignments
  - DBSCAN (eps=0.7, min_samples=10)
  - Clusters exceeding threshold → propose new top-level dimension
- `check_retirements()` → list[DimensionID]
  - Dimensions with no new evidence 2+ months AND confidence < 0.2

### `user_model/context.py` — ContextAssemblyV2
- `build_model_context(query, active_goals, max_tokens=300)` → str
  - Embed query, compute similarity to dimension descriptions
  - Filter to relevant dimensions
  - Inverse confidence weighting:
    - Sparse/conflicted → full treatment
    - Stable → one-liner
    - Goal-adjacent + uncertain → boosted
  - Include retrospective context notes where relevant
- `build_system_prompt(query, conversation_id)` → str
  - Layer 1: model context (≤300 tokens)
  - Layer 2: retrieved propositions annotated with dimension (≤400 tokens)

## Dependencies (dependencies.py after consolidation)

```python
# Single database
from app.services.storage.sqlite_storage import SQLiteStorage
from app.services.user_model.storage import UserModelStorage

db_path = settings.db_path  # unified voku.db
propositions_storage = SQLiteStorage(db_path)
user_model_storage = UserModelStorage(db_path)
embedder = BGEBaseEmbedding()
retrieval = RetrievalService(propositions_storage, embedder)

# User model services
assignment_service = AssignmentService(
    provider=get_provider("reasoning", sensitive=False)
)
exhale_service = ExhaleService(
    user_model_storage, embedder,
    provider=get_provider("reasoning", sensitive=True)
)
emergence_detector = EmergenceDetector(
    propositions_storage, user_model_storage, embedder
)
context_assembly = ContextAssemblyV2(
    user_model_storage, retrieval, embedder
)
```

## Testing Strategy

| Layer | What | How | Deterministic? |
|-------|------|-----|---------------|
| Storage | CRUD on user_model, model_evidence, seed loading | Unit tests with temp DB | ✅ Yes |
| Assignment parsing | Structured JSON → Assignment objects | Unit tests with mock LLM responses | ✅ Yes |
| Evidence mode | Temporal cue → experiential/retrospective | Unit tests with fixture propositions | ✅ Yes |
| Threshold gate | Semantic delta + confidence delta + citation check | Unit tests with fixture estimates | ✅ Yes |
| Emergence | Cluster detection within dimension / uncategorized | Unit tests: synthetic embeddings with known clusters | ✅ Yes |
| Assignment quality | 4-seed classification accuracy | Integration: 20 fixture props, assert ≥95% correct seed | ⚠️ Semi |
| Exhale pipeline | Evidence in → gated update out | Integration: 10 props per seed, verify reasonable estimate | ⚠️ Semi |
| Context assembly | Model state → formatted prompt | Snapshot tests: given model state, prompt matches template | ✅ Yes |
| End-to-end | Full pipeline from chat to model update | Manual + golden conversation set | ❌ Manual |
| **Generalization** | **Public journal data → coherent model** | **Reddit data test (see evaluation plan)** | ⚠️ Semi |

## Evaluation: Public Journal Data Test

Parallel track alongside implementation. Validates the architecture generalizes.

1. Collect 20-30 substantial Reddit posts from one user (r/selfimprovement, r/DecidingToBeBetter — users who post repeatedly over months)
2. Run extraction → do propositions look reasonable for stranger data?
3. Run assignment against 4 seeds → do propositions land in sensible places? Expect ≥90% correct seed.
4. Run emergence detection → do meaningful subdimensions get proposed?
5. Run exhale on emerged dimensions → do estimates make sense to human reader?
6. Compare: same data with 13 frozen dimensions → how many forced into bad fits?

Success: system builds coherent model of a stranger with no personal configuration.

## Build Sequence → Code Mapping

| Piece | Primary Files | Tests | Status |
|-------|--------------|-------|--------|
| 0 (DB consolidation) | `migrations/consolidate_db.py`, `config.py`, `dependencies.py` | All 52 existing tests pass on unified DB | ✅ DONE |
| 1 (Schema + seed) | `user_model/storage.py`, `data/dimension_seeds.json` | test_user_model_storage.py (29 tests) | ✅ DONE |
| 2 (Assignment P1) | `user_model/assignment.py` | test_assignment.py (22 tests — mock + integration) | ✅ DONE |
| 2b (Assignment P2 + evidence_mode) | `user_model/assignment.py` (extend) | test_assignment.py (17 more — score parsing + mock) | ✅ DONE |
| 5* (Phase space recolor) | `routes/propositions.py` + frontend `DataNode.tsx` | Visual verification | NEXT |
| 3 (Exhale) | `user_model/inference.py` | test_exhale.py (gate unit + integration) | |
| 3b (Emergence) | `user_model/emergence.py` | test_emergence.py (synthetic clusters) | |
| 4 (Context assembly v2) | `user_model/context.py`, `routes/chat.py` | test_context_assembly.py (22 tests) | ✅ DONE |
| 6 (Temporal trajectories) | Frontend phase space components | Visual verification | |
| 7 (Model view) | Frontend new view mode | Visual verification | |

## .gitignore Additions

```
# Personal data
docs/private/
data/*.db
data/dimension_seeds.local.json

# Already ignored
backend/venv/
backend/.env
```

## Public vs Private Docs

```
docs/
├── ANCHOR.md              # public — design philosophy
├── CONSTRAINTS.md         # public — engineering rules
├── BUILD4_SERVICE_PLAN.md # public — service architecture
├── USERMODEL_v2.md        # public — architecture with universal seeds
├── THEORY.md              # public — sanitize personal references before publishing
├── README.md              # public — portfolio piece
└── private/               # gitignored
    ├── STATE.md            # session state
    └── CONTINUE.md         # continuation prompts
```

USERMODEL.md is now safe to commit — 4 universal seeds contain no personal data. Personal dimension overrides live in gitignored `dimension_seeds.local.json`.