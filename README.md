# Voku

> *Renamed from BillyAI on Jan 31, 2026*

Multi-domain personal context architecture for fitness and finance data extraction, normalization, and analysis.

## Overview

Voku is a full-stack AI system that transforms unstructured data sources (workout screenshots, financial PDFs) into queryable structured records. Built with domain-extensibility as a first-class design principle.

**Core capabilities:**
- Vision-based data extraction from Apple Watch screenshots and fitness displays
- PDF transaction parsing and intelligent categorization
- Variable registry for name normalization across sessions
- Multi-domain architecture (fitness + finance, extensible to N domains)
- React frontend with content-driven theming

**Use case:** Personal cognitive prosthetic. Upload a workout screenshot or bank statement → structured data with semantic search (v0.3).

## Architecture

### Backend
- **Framework:** FastAPI with router-based domain separation
- **Vision:** Provider abstraction (Groq for speed, Ollama for privacy)
- **Storage:** SQLite (operational data) + JSON sessions (raw extracts)
- **Intelligence:** LLM-based merchant categorization with learning cache
- **Testing:** 64 tests (pytest) across 6 modules

### Frontend
- **Stack:** Vite + React + TypeScript + Tailwind v4
- **UI:** shadcn/ui components with custom theming
- **Design:** Mixed-theme system (light for text-heavy content, dark for metrics)
- **Pages:** 6 functional routes across fitness and finance domains

### Key Architectural Decisions
- **Provider abstraction:** Route workloads based on requirements (speed vs. privacy)
- **Variable registry:** Human-in-the-loop feedback for name normalization
- **Domain color systems:** Fitness (orange/red), Finance (cyan/violet) for spatial distinction
- **LangChain-free:** Direct API control for observability and debugging

## Features

### Fitness Domain
- **Training Session Log:** Drag-drop image upload with extraction display
- **Session History:** Master-detail view with chronological filtering
- **Variable Registry:** Auto-normalize metrics (e.g., "Avg HR" → "average_heart_rate")

### Finance Domain
- **PDF Import:** Batch transaction extraction from bank statements
- **Transaction List:** Filterable data table with category breakdown
- **Monthly Summary:** Aggregate spending by category with metrics cards
- **Smart Categorization:** LLM-powered merchant categorization with learning

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Pydantic, SQLite |
| Vision | Groq API (llama-4-scout), Ollama (local fallback) |
| Frontend | React 18, TypeScript, Tailwind v4, shadcn/ui |
| Build | Vite, pnpm |
| Testing | pytest (backend), 64 passing tests |
| Deployment | Target: Hugging Face Spaces / Railway (March 2026) |

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add GROQ_API_KEY to .env

# Run tests
python -m pytest -v

# Start server
uvicorn app.main:app --reload
# API available at http://localhost:8000
```

### Frontend

```bash
cd frontend
pnpm install
pnpm run dev
# Open http://localhost:5173
```

## API Usage

### Fitness

```bash
# Log training session
curl -X POST http://localhost:8000/log/training/session \
  -F "image=@data/test_images/apple_fitness/indoor_cycle_summary.png"

# Get session history
curl http://localhost:8000/fitness/sessions
```

### Finance

```bash
# Import PDF transactions
curl -X POST http://localhost:8000/finance/import \
  -F "file=@data/finance/imports/CAD_Toss.pdf"

# List transactions
curl http://localhost:8000/finance/transactions

# Monthly summary
curl "http://localhost:8000/finance/summary?month=2026-01"
```

## Project Status

**Current Phase:** v0.2 UI Development (Target: Feb 21, 2026)

| Milestone | Status | Target |
|-----------|--------|--------|
| v0.1: Backend Pipeline | ✅ Complete | — |
| v0.2: Multi-Domain UI | 🟡 In Progress | Feb 21 |
| v0.2.5: Production Signals | Planned | Mar 10 |
| v0.3: Semantic Search (ChromaDB) | Planned | Mar 15 |
| Demo Deployment | Planned | Mar 31 |

See [STATE.md](./STATE.md) for detailed implementation status and technical debt tracking.

## Development Principles

1. **TDD for core logic** — 64 tests covering extraction, parsing, normalization
2. **Evidence-based design** — Research-backed UX decisions (see MIXED_THEME_RATIONALE.md)
3. **Domain extensibility** — Architecture supports N domains, not hardcoded to fitness/finance
4. **Local-first privacy** — Sensitive data processing via Ollama, no external API calls
5. **Production-ready thinking** — Health checks, structured logging, request tracing planned for v0.2.5

## Documentation

- **[STATE.md](./STATE.md)** — Current implementation status, blockers, decisions
- **[docs/API.md](./docs/API.md)** — Endpoint contracts and usage
- **[docs/DESIGN.md](./docs/DESIGN.md)** — Architecture and design notes
- **[docs/MIXED_THEME_RATIONALE.md](./docs/MIXED_THEME_RATIONALE.md)** — Evidence-based design defense
- **[PROJECT_RULES.md](./PROJECT_RULES.md)** — Development guidelines

## Roadmap

### Completed ✅
- Vision extraction from Apple Watch screenshots
- JSON session persistence with metadata
- Variable registry with alias support
- Provider abstraction (Groq + Ollama)
- Finance PDF parsing and categorization
- FastAPI router architecture
- React frontend with 6 functional pages
- Mixed-theme design system
- 64 passing tests across 6 modules

### In Progress 🟡
- UI review flow for unknown variable confirmation

### Planned 📋
- Health check endpoints (liveness, readiness)
- Structured JSON logging with request IDs
- Error path testing and LLM mocking
- ChromaDB semantic search integration
- Deployment to Hugging Face Spaces / Railway

### Deferred
- Docker containerization (May 2026)
- Multi-image session merging
- Health app data import
- Trainer agent (actual vs. planned comparison)

## Interview Talking Points

**Why no LangChain?**  
Direct API control provides full observability and debugging capability. 45% of developers who try LangChain never use it in production (2025 survey). Short-term convenience trades for long-term technical debt.

**Why SQLite?**  
Single-user local-first design prioritizing privacy. Configured with WAL mode for concurrency. Migration path to PostgreSQL documented for multi-user scaling.

**Why ChromaDB?**  
Appropriate for portfolio scale with local-first philosophy. Production horizontal scaling would evaluate Qdrant or managed Pinecone.

**Design decisions?**  
Mixed-theme system is evidence-based: Piepenbrock research shows 20-26% reading speed advantage for positive polarity (light mode for tables). Dark mode for metrics leverages Helmholtz-Kohlrausch effect for data visualization.

## License

MIT

---

**Built by:** Jaymin Chang  
**Portfolio:** [github.com/jmin1219](https://github.com/jmin1219) | [@ChangJaymin](https://twitter.com/ChangJaymin)  
**Timeline:** v0.1 completed 6 weeks ahead of schedule (Jan 2026)  
**Repo:** https://github.com/jmin1219/voku
