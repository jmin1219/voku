# Voku — Transparent Thinking Environment for AI Agents

A personal knowledge graph that builds itself from conversation. Every message becomes a timestamped trace. Traces connect through semantic similarity, temporal sequence, and intentional links. The graph that emerges becomes the context layer any AI agent can query — and the user can see exactly what the system knows.

<!-- TODO: Add screenshots -->
<!-- ![Phase Space](docs/screenshots/phase-space.png) -->
<!-- ![Chat with Context Markers](docs/screenshots/chat-context.png) -->

## What It Does

You talk to an AI. Each message becomes an immutable trace, embedded and stored. Over time, traces cluster into themes. The AI retrieves relevant traces to build contextually rich responses — and shows you exactly which traces it used via inline citations. A 3D phase space lets you explore the topology of your thinking at any resolution.

**869 traces** · **271 tests** · **7,600 LOC** · **~120 hours**

## Architecture

```
traces          Immutable conversational records (timestamp, content, source)
annotations     LLM-extracted metadata (category-free, re-extractable)
connections     Typed edges (semantic | temporal | intentional | supersedes)
resources       External references anchored to introduction moment
embeddings      bge-base-en-v1.5 vectors (768d, in-memory cosine search)
```

Five tables in a single SQLite file. Traces are permanent ground truth. Everything else is computed and replaceable.

### Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, SQLite (WAL mode) |
| Embeddings | bge-base-en-v1.5 via sentence-transformers, numpy cosine search |
| LLM (chat) | Anthropic Claude (streaming) |
| LLM (extraction) | Groq llama-3.3-70b (async annotation extraction) |
| Frontend | React 19, TypeScript, Vite, Tailwind v4 |
| Visualization | Three.js via react-three-fiber, InstancedMesh rendering |
| Deployment | Docker (multi-stage build) |


## Key Technical Decisions

**Custom graph over external DB.** At <10K traces, SQLite with in-memory numpy cosine search handles vector retrieval in <10ms. No Pinecone, no Kuzu, no server dependency. Single-file database — `cp voku.db backup.db` is the backup strategy.

**Traces over propositions.** v1 extracted propositions (atomic claims) from conversations. v2 stores raw conversational traces and computes annotations on top. The raw stream is richer than any extraction — and annotations can be recomputed with better models without losing ground truth.

**Cosine + graph expansion retrieval.** Vector similarity alone misses temporal context. Retrieval expands 1-hop along temporal and intentional connections, weights by recency (exponential decay), and boosts traces with intention/commitment annotations (1.3x). Contradiction detection surfaces evolving beliefs.

**Hierarchical DBSCAN clustering.** Fine clusters (eps=0.15 cosine distance) capture topic-level groupings. Orientation clusters (eps=0.4 on centroids) reveal broader life themes. No predefined categories — structure emerges from the data.

**Category-free annotations.** No predefined types at the schema level. The LLM extraction model produces whatever types fit the content — measurables, decisions, emotions, commitments, topics. Structure emerges from use, not from developer intuition.

## What I Learned

- **Retrieval dominates write strategy.** Yuan et al. (2025) showed a 20-point accuracy gap from retrieval method vs 3-8 points from write strategy. Voku's cosine-only retrieval is the primary bottleneck — BM25 + hybrid reranking is the highest-leverage next improvement.
- **Anti-collapse as design principle.** Every AI memory system collapses users into point estimates (profiles, summaries). Voku preserves the cloud — contradictory traces coexist, pattern-opinions are scoped and revisable, the system never says "you are X."
- **InstancedMesh scales.** 869 nodes + 4,345 edges render at 60fps in a single draw call. Three.js via react-three-fiber makes GPU-accelerated graph visualization accessible.


## Run It

```bash
# Docker (recommended)
cp .env.example .env
# Edit .env with your API keys (Anthropic for chat, Groq for annotations)
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

## Seed Demo Data

The Docker image ships with a pre-seeded database (869 traces). To regenerate from session logs:

```bash
cd backend && source venv/bin/activate
python scripts/seed_from_sessions.py \
  --sessions-dir /path/to/session/logs \
  --wipe
```

## Docs

| Document | Purpose |
|----------|---------|
| [SPEC.md](docs/SPEC.md) | Architecture, data model, design philosophy |
| [CONSTRAINTS.md](docs/CONSTRAINTS.md) | Design decision hierarchy |
| [CLAUDE.md](CLAUDE.md) | Dev context for AI-assisted development |

## License

MIT

---

Built by Jaymin Chang — MSCS @ Northeastern Vancouver
