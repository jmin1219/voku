# Voku v0.3 Implementation — Continuation Prompt

> *Renamed from BillyAI on Jan 31, 2026*

## Context
Voku v0.3 architecture finalized. Goal-anchored philosophy defined (Jan 30). Repo public at https://github.com/jmin1219/voku

## Core Philosophy
**Voku is not a productivity planner — it's the derivative of that.** Self-understanding is the anchor; goals emerge from seeing yourself clearly. Core function: surface discrepancies between stated intentions and observed patterns.

## Phase A: Kuzu Foundation

**Directory structure to create:**
```
backend/app/services/graph/
├── __init__.py
├── database.py    # Kuzu connection singleton
├── schema.py      # CREATE TABLE statements
├── operations.py  # CRUD operations
└── queries.py     # Complex Cypher queries

backend/tests/
└── test_graph.py  # Graph integrity tests
```

**Sequence:**
1. `pip install kuzu`
2. Create `database.py` — connection management
3. Create `schema.py` — all table definitions from DESIGN_V03.md Section 6
4. Create `operations.py` — basic CRUD for each node type
5. Write tests — create/read/update/delete + edge creation
6. Verify bi-temporal fields work correctly

## Schema Summary

**4 Node Tables:**
- `RootNode` — Modules with intentions JSON
- `InternalNode` — Abstractions with node_purpose/source_type/signal_valence
- `LeafNode` — Extracted from conversation, same 3 new fields
- `OrganizationNode` — Voku's hidden workspace (type field)

**6 Edge Tables:**
- `CONTAINS`, `SUPPORTS`, `CONTRADICTS`, `ENABLES`, `SUPERSEDES`, `REFERENCES`

**1 Embedding Table:**
- `NodeEmbedding` — node_id, embedding_type, embedding[768]

## Key Files
- `docs/DESIGN_V03.md` Section 6 — Complete Kuzu schema
- `docs/STATE.md` — Implementation phases checklist

## Mode
DSA mode — you explain, you write code, I guide with hints and probing questions.
