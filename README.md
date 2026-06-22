# Voku

A conversational knowledge graph with temporal retrieval and 3D visualization.

**[Architecture](#architecture)** · **[Design Decisions](#design-decisions)** · **[What I Learned](#what-i-learned)** · **[Run It](#run-it)**

> **Status:** Research prototype, v2 complete. Runs locally via `docker compose up`. No hosted demo — the system was built as a thinking environment to use personally, not as a SaaS. Walkthrough available on request.

---

## What It Does

You talk to an AI. Every message becomes an immutable **trace** — timestamped, embedded, and stored. Over time, traces connect through semantic similarity, temporal sequence, and intentional links. Clusters emerge through hierarchical DBSCAN. The AI retrieves context by combining vector search with graph expansion, and shows you exactly which traces it used via inline citations. A 3D phase space lets you orbit through the topology of accumulated knowledge.

**271 tests** · **~7,600 LOC** · **Python/FastAPI + React/TypeScript + Three.js** · **Single-file SQLite**

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│  React 19 · TypeScript · Tailwind v4             │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │  Chat Panel  │  │  3D Phase Space          │  │
│  │  streaming   │  │  Three.js/R3F            │  │
│  │  context [1] │  │  InstancedMesh (60fps)   │  │
│  │  /digest cmd │  │  cluster shells, edges   │  │
│  └─────────────┘  └──────────────────────────┘  │
└────────────────────────┬────────────────────────┘
                         │ /api
┌────────────────────────┴────────────────────────┐
│                   Backend                        │
│  FastAPI · Python 3.13                           │
│                                                  │
│  Trace Storage ──→ Embedding (bge-base, 768d)    │
│       │                    │                     │
│       ▼                    ▼                     │
│  Connections          Vector Search              │
│  (temporal,           (numpy cosine,             │
│   semantic,            in-memory)                │
│   intentional,              │                    │
│   supersedes)               ▼                    │
│       │              Graph Expansion             │
│       ▼              (1-hop temporal +            │
│  Annotations          intentional, recency       │
│  (LLM-extracted,      decay, intention boost)    │
│   category-free)            │                    │
│       │                     ▼                    │
│       ▼              Context Assembly            │
│  Contradiction       (system prompt with         │
│  Detection            evolution cues)            │
│       │                     │                    │
│       ▼                     ▼                    │
│  Hierarchical         Temporal Digest            │
│  Clustering           (period summaries,         │
│  (DBSCAN, 2-level)     topic evolution)          │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  SQLite (WAL mode) — single file          │   │
│  │  traces · annotations · connections ·     │   │
│  │  embeddings · resources                   │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

## Design Decisions

**Traces over propositions.** v1 extracted atomic propositions from conversations. They were lossy — stripping tone, context, and ambiguity. v2 stores raw conversational traces and computes annotations on top. The raw stream is richer than any extraction, and annotations can be recomputed with better models without losing ground truth.

**SQLite over a vector database.** At sub-10K traces, in-memory numpy cosine search runs in <10ms. No Pinecone, no Kuzu, no server dependency. One file. `cp voku.db backup.db` is the backup strategy. The complexity of external vector services costs more than it buys at this scale.

**Graph expansion follows temporal and intentional connections, not semantic ones.** Semantic expansion creates echo chambers — you retrieve what's similar to what's similar. Temporal expansion retrieves what was said *around the same time*, which captures conversational context. Intentional expansion follows links the user explicitly drew. This produces retrieval that feels contextually grounded rather than topically narrow.

**Category-free annotations.** No predefined taxonomy at the schema level. The LLM extraction model produces whatever types fit the content — decisions, emotions, commitments, measurables. Structure emerges from use, not from developer intuition. This means the system adapts to any domain without schema changes.

**Anti-collapse.** Every AI memory system I looked at collapses users into point estimates — profiles, summaries, preference vectors. Voku preserves contradictions as coexisting traces. Pattern-opinions use provisional language ("~N decisions about..."). The system never says "you are X." No edit buttons, no regenerate, no forced resolution. Beliefs exist in tension until the user resolves them through conversation.

**Hierarchical DBSCAN over k-means.** Two levels — fine clusters (eps=0.15 cosine distance) for topics, orientation clusters (eps=0.4 on centroids) for life themes. DBSCAN doesn't require specifying k, handles noise gracefully, and produces clusters of varying density. Structure is discovered, not imposed.

## What I Learned

**Retrieval dominates write strategy.** Yuan et al. (2025) showed a 20-point accuracy gap from retrieval method versus 3–8 points from write strategy. My initial instinct was to invest in better extraction. The literature says invest in better retrieval. Cosine-only search is the current bottleneck — BM25 hybrid reranking is the highest-leverage next improvement.

**InstancedMesh scales.** 869 nodes + 4,345 edges render at 60fps in a single draw call via Three.js/react-three-fiber. GPU-accelerated graph visualization is more accessible than I expected. The bottleneck is the projection (UMAP), not the rendering.

**The system prompt is underrated as an architecture surface.** Context assembly — deciding what goes into the system prompt and how — is where retrieval quality becomes conversation quality. The system prompt carries contradiction evolution cues, resurfaced traces, and temporal context. It's not an afterthought; it's the primary integration point.

## What I'd Build Next

The deeper question behind Voku is: **how do you model someone who's changing?** Voku preserves the raw material but doesn't model the dynamics. The next step is active inference — a generative model that maintains beliefs about a person, updates them through observation, and acts to reduce uncertainty. The knowledge graph becomes the state space; retrieval becomes inference; the system prompt becomes a policy. That's a different project, grounded in the same question.

## Run It

```bash
# Docker (recommended)
cp .env.example .env
# Add your API keys: ANTHROPIC_API_KEY (chat), GROQ_API_KEY (annotations)
docker compose up --build
# Open http://localhost:8000
```

```bash
# Local development
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add API keys
uvicorn app.main:app --reload

cd frontend
NODE_ENV=development npm install
npm run dev
```

```bash
# Tests
cd backend && source venv/bin/activate
pytest  # 271 tests
```

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, SQLite (WAL mode) |
| Embeddings | bge-base-en-v1.5 (768d), in-memory numpy cosine search |
| LLM (chat) | Anthropic Claude (streaming) |
| LLM (extraction) | Groq llama-3.3-70b (async annotation extraction) |
| Frontend | React 19, TypeScript, Vite, Tailwind v4 |
| Visualization | Three.js via react-three-fiber, InstancedMesh |
| Deployment | Docker (multi-stage build) |

## License

MIT

---

Built by [Jaymin Chang](https://linkedin.com/in/jaymin-chang-professional) — MS Computer Science, Northeastern University Vancouver
