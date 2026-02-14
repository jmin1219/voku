# Voku

> Personal context engine that ingests conversations, extracts beliefs, tracks how they evolve, and serves temporally-aware context back to AI tools.

## The Problem

Every AI conversation starts from scratch. Claude's memory stores compressed summaries that mutate over time. Your beliefs evolve — you change your mind, refine your thinking, develop new understanding — but no tool tracks that evolution. Flat memory systems remember *what* you said. They don't know *when* you stopped believing it.

## What Voku Does

Voku sits underneath your existing AI workflow. It ingests exported conversations, extracts atomic propositions (beliefs, observations, decisions), and stores them with full temporal provenance. A process engine then detects when beliefs contradict or supersede each other, building an evolving model of how you think.

**The demo moment:** Ask "What is the user's main rowing limiter?" Flat retrieval returns *ankle* (mentioned first, mentioned more). Voku returns *breathing* (most recent, supersedes ankle) — with a timeline showing the evolution and evidence trail.

## Architecture

```
Conversation Export (.md)
    → Parser (Component 1.1)
        → ConversationMessage (text + who + when + provenance)
            → ExtractionService (Groq/Ollama LLM)
                → Proposition (belief + type + confidence)
                    → EmbeddingProvider (BGE-base, 768-dim)
                        → Dedup (cosine similarity > 0.95)
                            → SQLite (propositions + embeddings)

Process Engine (post-ingestion):
    → Find similar proposition pairs
    → LLM classifies: SUPPORTS / CONTRADICTS / SUPERSEDES
    → Update statuses, create edges
    → Build thread surfaces (topic summaries)

Serving:
    → MCP server → Claude Desktop gets temporally-aware context
    → Evaluation harness → golden test set, temporal accuracy metrics
```

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Storage | SQLite + numpy | Single portable file. In-memory vector search via numpy. No vector DB overhead. |
| Embeddings | bge-base-en-v1.5 | 768-dim, sentence-transformers. Spike S2 confirmed over EmbeddingGemma. |
| LLM (default) | Groq | llama-3.3-70b-versatile, free tier. Auto-fallback to Ollama if no API key. |
| LLM (local) | Ollama | Zero-cost default. Privacy-first for sensitive data. |
| Backend | FastAPI | Lightweight, async-native. |
| MCP | FastMCP | stdio transport, Claude Desktop integration. |
| Evaluation | Custom + RAGAS | Temporal accuracy metric, golden test set, ablation studies. |

## Current Status

**Milestone 1: Ingest Real Data — ✅ COMPLETE**
- Parser, SQLite storage, BGE embedding, ingestion pipeline
- 29 tests passing (28 unit + 1 integration gate with real Groq + BGE)
- 13 commits, spec-driven development

**Milestone 2: Prove Retrieval Works — 🎯 Next**
- Golden test set, retrieval service, evaluation harness
- Establish flat retrieval baseline (the number to beat)

**Milestone 3: Prove Temporal Tracking — The Thesis**
- Process engine: contradiction/supersession detection via LLM
- Temporal retrieval: returns current beliefs, not just most-mentioned
- Gate test: temporal accuracy > flat accuracy on real belief evolution

**Milestone 4: Make It Usable — Flex Scope**
- MCP server serving context to Claude Desktop
- Optional visualization (simplify if time-constrained)

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite over graph DB | Kuzu archived. Single file, portable, numpy handles vector search at personal scale. |
| Meaning at read-time | No pre-computed edges in storage. Process engine discovers relationships post-ingestion. |
| Explicit beliefs only | Extraction accuracy on implicit beliefs (~40-60% F1) makes end-to-end temporal accuracy coin-flip. Demo scope: first-person declarative statements. |
| Evaluation-first | "Temporal accuracy improved X% over flat retrieval" gets interviews. Metrics are first-class deliverables. |
| Local-first, zero-cost default | Every component works without paid APIs. Ollama fallback automatic. |
| Batch import, no chat UI | Prove thesis with real data + evaluation metrics. Chat UI is delivery mechanism, not the thesis. |

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add GROQ_API_KEY (optional — falls back to Ollama)

# Run all tests
python -m pytest tests/ -v

# Run integration gate (requires GROQ_API_KEY)
python -m pytest tests/test_milestone1.py -v
```

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/STATE.md](./docs/STATE.md) | Implementation status, session log, decisions |
| [docs/CONTINUE.md](./docs/CONTINUE.md) | Session continuation prompt |
| [docs/COMPONENT_SPEC.md](./docs/COMPONENT_SPEC.md) | Full build spec — 10 components, 4 milestones |
| [docs/CONSTRAINTS.md](./docs/CONSTRAINTS.md) | Hierarchical decision framework (4 tiers) |

## License

MIT

---

**Built by:** Jaymin Chang — MSCS @ Northeastern Vancouver
**Portfolio:** [github.com/jmin1219](https://github.com/jmin1219) | [@ChangJaymin](https://twitter.com/ChangJaymin)
