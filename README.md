# Voku

> An observation engine that models how a person allocates attention, time, and energy — and reflects that model back so they can see what they actually prioritize, how their understanding evolves, and where their stated intentions diverge from their revealed behavior.

## Why

Every AI memory system points output at the AI. Mem0 remembers so the chatbot can personalize. Graphiti tracks facts so the agent can reason. Voku flips the audience: the AI is infrastructure, the human is the one looking into the mirror.

The problem: humans can't inspect their own cognitive processes. Nuanced evaluations flatten into harsh verdicts through repeated recall. Physical states silently degrade cognition. Tools that require self-knowledge to configure are useless to those who lack it. Voku addresses these by externalizing what's invisible — not to tell people what to think, but to make the inputs to their intuition inspectable.

> *"The system doesn't discover who the user is. It co-creates a useful model of who they're becoming."*

## Three Capabilities

1. **Stance tracking** — beliefs evolve via supersession. "Ankle is my rowing limiter" → "Breathing is my rowing limiter." Temporal provenance preserves the full evolution chain.

2. **Behavioral pattern detection** — events accumulate, patterns emerge from frequency and correlation. "Scrolled after lunch 4 of 5 weekdays." Surfaces what the user can't see from inside the pattern.

3. **Stated-vs-revealed gap detection** — intentions compared against events. The discrepancy between what you say you'll do and what you actually do is the most diagnostic signal about who you actually are.

## Architecture

```
Conversation Exports (.md)
    → Parser → ConversationMessage (text + speaker + timestamp + provenance)
        → ExtractionService (Groq/Ollama)
            → Proposition (stance | event | intention) + confidence
                → EmbeddingProvider (bge-base, 768-dim)
                    → SQLite (propositions + embeddings + edges)

Processing (post-ingestion):
    → Stance pipeline: supersession/contradiction detection
    → Event pipeline: pattern accumulation + frequency analysis
    → Intention pipeline: fulfillment tracking against events

Serving:
    → MCP server → Claude Desktop receives temporally-aware context
    → Evaluation harness → temporal accuracy metrics + ablation studies
```

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Storage | SQLite + numpy | Single portable file. In-memory vector search. No infrastructure. |
| Embeddings | bge-base-en-v1.5 | 768-dim. Spike-validated over EmbeddingGemma. |
| LLM | Groq → Ollama fallback | Zero-cost default. Auto-fallback if no API key. |
| MCP | FastMCP | stdio transport, Claude Desktop integration. |
| Evaluation | Custom temporal metric + RAGAS | Ablation: flat vs temporal retrieval. |

## Version Roadmap

| Version | Question | Status |
|---------|----------|--------|
| **v0** | Does temporal tracking outperform flat retrieval? | 🏗️ Building — M1 complete, extraction redesign next |
| **v1** | Can Voku reliably observe stance evolution, patterns, and intention gaps? | Planned |
| **v2** | Can belief network structure reveal things individual tracking can't? | Research |
| **v3** | Can a self-referential feedback system manage its own observer effects? | Vision |

## Current Status

**Milestone 1: Ingest Real Data — ✅ COMPLETE** (29/29 tests)

**Next: v0 Phase 1 — Clean Foundation**
- Re-extraction prompt (user messages only, 3 node types)
- Node type classification validation (stance/event/intention)
- Relationship classification spike (SUPPORTS/CONTRADICTS/SUPERSEDES)

## Setup

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # GROQ_API_KEY optional — falls back to Ollama

pytest tests/ -v                      # Unit tests
pytest tests/test_milestone1.py -v    # Integration gate (needs Groq key)
```

## Docs

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Top-down build plan + version roadmap |
| [COMPONENT_SPEC.md](./docs/COMPONENT_SPEC.md) | Component interfaces + test specs |
| [CONSTRAINTS.md](./docs/CONSTRAINTS.md) | Hierarchical decision framework |
| [STATE.md](./docs/STATE.md) | Implementation status + session log |

## License

MIT

---

**Built by:** Jaymin Chang — MSCS @ Northeastern Vancouver
[@ChangJaymin](https://twitter.com/ChangJaymin)
