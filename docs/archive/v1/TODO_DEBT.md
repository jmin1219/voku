# Voku — Code TODOs & Technical Debt

> Compiled Feb 21, 2026. Covers all `.py`, `.ts`, `.tsx`, `.jsx`, `.css`, config files.

---

## Commented TODOs in Code

### 1. ~~`backend/app/main.py:22-23`~~ — ✅ DELETED Feb 21
```python
# TODO: Initialize SQLite storage (Component 1.2)
# TODO: Initialize embedding service (Component 1.3)
```
**Status:** Already done — `dependencies.py` handles shared singletons at import time. The lifespan function only creates the data directory. These TODOs are leftovers from the original scaffold.
**Action:** Remove both lines. The lifespan function's `db_path.parent.mkdir()` is still useful; the TODOs are dead.

### 2. `backend/tests/test_parser.py:116` — OPEN
```python
def test_roundtrip_known_output():
    # TODO: create small synthetic fixture with exact expected output
    pass
```
**Status:** Placeholder test that currently passes by doing nothing. The parser works (other tests cover it), but there's no golden-output roundtrip test.
**Action:** Low priority. Create a small synthetic `.md` fixture with known parse output if parser changes in Build 4+. Not blocking.

---

## Implicit Debt (from state.md / Known Issues, no code comments)

### 3. `NODE_ENV=production` in `~/.zshrc`
**Impact:** Forces `NODE_ENV=development` prefix on every `npm install` in frontend. 
**Action:** Remove from shell config. One-time fix.

### 4. `propositions.py` — Inline UMAP computation (~120 lines)
**Impact:** The route handler does UMAP projection, DBSCAN clustering, scaling, and node assembly inline. Will get worse as Build 4 adds dimension coloring.
**Action:** Extract to `services/projection.py` before or during Piece 5 (phase space recolor). Natural extraction point.

### 5. Unclustered nodes (cluster=-1) — default styling
**Impact:** 55 nodes at eps=0.7 get `cluster=-1`, rendered with default color. No visual distinction from clustered nodes.
**Action:** Distinct styling (e.g., muted color, smaller radius). Can address during Piece 5 recolor.

### 6. `main.py` lifespan — doesn't initialize shared services
**Impact:** Storage + embedding are initialized at import time in `dependencies.py`, not in the lifespan. This works but means no clean shutdown (`.close()` never called).
**Action:** Low priority — SQLite handles this fine via OS-level cleanup. Could wire up `propositions_storage.close()` in lifespan's shutdown phase if we want clean teardown.

---

## Summary

| # | Location | Type | Priority | When |
|---|----------|------|----------|------|
| 1 | ~~`main.py:22-23`~~ | ~~Stale TODO~~ | ~~Trivial~~ | ✅ Deleted Feb 21 |
| 2 | `test_parser.py:116` | Missing test | Low | If parser changes |
| 3 | `~/.zshrc` | Env config | Quick fix | Anytime |
| 4 | `propositions.py` | Inline computation | Medium | Piece 5 |
| 5 | Frontend `DataNode.tsx` | Missing styling | Low | Piece 5 |
| 6 | `main.py` lifespan | No clean shutdown | Low | Optional |
