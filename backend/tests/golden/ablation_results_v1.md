# Ablation v1 Results — Feb 16, 2026

## Summary

| Mode | Pass Rate | Avg Precision |
|------|-----------|---------------|
| Flat (tw=0.0) | 11/14 (79%) | 0.82 |
| Temporal (tw=0.3) | 8/14 (57%) | 0.61 |

**Flat wins.** Temporal weighting at 0.3 is too aggressive — recency overwhelms semantic relevance.

## Root Cause Analysis

### Problem: Recency overwhelms similarity
- Voku-related propositions (Feb 11, 2026) have recency scores ~0.88
- Older but MORE RELEVANT propositions get pushed out
- Example: "Where does the user live?" → temporal mode returns Voku architecture props instead of "Moved to Vancouver"
- Example: "Cooking preferences?" → temporal mode returns caloric intake instead of chicken/oven props

### Problem: Similarity threshold too low
- threshold=0.3 lets irrelevant props leak into results
- Topic timeline returns 50 items for "database choice" — most unrelated
- Current belief for "breathing" topic = Voku prop (wrong domain entirely)

### Problem: Golden set expectations may be misaligned
- GS10 "afternoon murk" — the word "murk" doesn't appear in any proposition (it's an internal vocabulary term)
- GS12 "currently working on" + expected "Voku" — Voku props exist but describe architecture, not "I am working on Voku"
- GS01 "Where does the user live?" — "Vancouver" is in "Moved to Vancouver" but similarity=0.588 is low

## What Went Right (Flat mode)
- GS03 (net worth): 0.810 similarity, correct first hit
- GS04 (time-blocking): 0.696, two correct hits in top 3
- GS06 (database): 0.760, SQLite is first result
- GS09 (breathing): 0.792, nasal breathing first result
- GS11 (interest rates): 0.806, superseded prop found

## Next Steps

1. **Raise similarity threshold** to 0.4-0.5 for cleaner results
2. **Reduce temporal weight** to 0.1-0.15 — gentle boost, not dominance
3. **Fix golden set** — update expected texts to match actual proposition wording
4. **Topic timeline needs domain filtering** — pure similarity with high threshold
5. **Re-run ablation** after adjustments

## Raw Scores

### Flat Mode Failures
- GS02 (education): "Columbia" not in top 5. Prop exists but similarity too low for "educational background" query.
- GS10 (afternoon murk): "murk" not in any proposition text.
- GS12 (currently working on): "Voku" props describe architecture, not work activity.

### Temporal Mode Additional Failures
- GS01 (location): Vancouver prop pushed out by recent Voku props
- GS07 (social life): "lonely" prop (Sep 2025) pushed out by recency
- GS14 (cooking): Chicken/oven props (Sep 2025) pushed out by caloric intake (Feb 2026)
