# Voku Continuation Prompt

> Use this to resume work in a new chat session.

---

## Context

**Project:** Voku v0.3 — Knowledge-first cognitive prosthetic
**Phase:** A (Kuzu Foundation) — ~75% complete
**Last Session:** Feb 01, 2026

## What's Done

- Schema complete (5 node tables, 6 edge tables)
- Node CRUD: `create_module()`, `create_leaf_node()`, `get_node()`
- Edge operations: `create_edge()`, `get_children()`
- `constants.py` with `EDGE_CONSTRAINTS` validation
- 13 tests passing

## What's Next

**Remaining Phase A work:**

1. **`create_internal_node()`** — Currently stubbed in operations.py
   - Same fields as LeafNode but represents abstractions (clusters of beliefs)
   - Needed for hierarchical organization (Module → Internal → Leaf)

2. **`get_related(node_id, rel_type)`** — Currently stubbed
   - Traverse SUPPORTS, CONTRADICTS, ENABLES, SUPERSEDES edges
   - Optional rel_type filter (None = all relationships)

3. **Optional: node_purpose validation**
   - Enum constraint: observation, pattern, belief, intention, decision
   - Test is currently skipped

## Key Files

```
backend/app/services/graph/
├── constants.py      # EDGE_CONSTRAINTS, VALID_EDGE_TYPES
├── schema.py         # Kuzu table definitions  
└── operations.py     # Graph CRUD (add methods here)

backend/tests/test_graph.py  # Add tests here (TDD)
docs/STATE.md               # Update after each session
```

## TDD Workflow

1. Write test first in `test_graph.py`
2. Run: `cd backend && python -m pytest tests/test_graph.py -v`
3. Implement in `operations.py`
4. Verify test passes

## Run Tests

```bash
cd /Users/jayminchang/Documents/projects/voku/backend
source venv/bin/activate
python -m pytest tests/test_graph.py -v
```

## Resume Command

"Continue Voku Phase A — implement `create_internal_node()` and `get_related()`. TDD workflow: write test first, then implement."
