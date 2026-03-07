# Demo Script — Voku (≤90 seconds)

## Setup
```bash
docker compose up  # or local dev servers
# Open http://localhost:8000
```

## Walkthrough

### 1. Open — The Graph (10s)
Open the phase space (⌘+Space). 869 traces, 34 clusters, 4,345 connections. Point out visible cluster separation — career, academics, training, voku development, emotional processing. This is two months of daily thinking, structured automatically.

### 2. Cross-Session Question (20s)
Type: **"How has my thinking about career direction evolved?"**

Watch: Context markers [1] [2] [3] appear in the response. The AI pulls traces from across weeks — career planning, north star questioning, co-op research. In the phase space, retrieved nodes glow gold.

**Fallback query:** "What patterns do you see in my recent conversations?"

### 3. Explore the Phase Space (15s)
Hover traces — see content previews, timestamps, source types. Click a cluster — see it's labeled with extracted keywords. Zoom out — clusters merge into broader orientations. The topology of two months of thinking, visible at a glance.

### 4. Temporal Digest (20s)
Click the **#digest** button (or type `/digest`).

The AI synthesizes a narrative — not a list — covering themes, evolution, contradictions, and open questions from the trace graph. Context markers throughout link back to specific moments.

### 5. Close — The Thesis (15s)
"869 traces, 34 clusters, 4,345 connections. Three primitives — traces, connections, annotations. The graph emerges from conversation. The chat uses it for context. The visualization makes it transparent. No predefined categories, no hidden profiles — structure emerges from use."

## Pre-Tested Queries

| Query | What it shows |
|-------|--------------|
| "How has my thinking about career direction evolved?" | Cross-session retrieval, contradiction surfacing |
| "What have I been going back and forth on?" | Evolution detection, temporal range |
| "What patterns do you see in my recent conversations?" | Pattern detection, multi-domain awareness |
| `/digest` or #digest button | Period summary narrative |

## If Chat Fails (No API Key)
Phase space still renders (pre-computed). History still loads. Point to the graph structure and explain the retrieval pipeline verbally.
