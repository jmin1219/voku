# Voku

A personal digital environment where you think out loud through conversation and watch your knowledge structure take shape in real time.

Chat on the left, 3D phase space on the right. As you talk, the system extracts propositions, positions them by semantic similarity, and activates relevant nodes based on what you're saying now. Structure emerges from the data — no manual organization.

## Stack

**Frontend:** React 19 + TypeScript + Tailwind v4 + Three.js (react-three-fiber)
**Backend:** FastAPI + SQLite + bge-base-en-v1.5 embeddings + Groq/Ollama LLM providers

## Setup

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
pytest tests/ -v

# Frontend
cd frontend
npm install
npm run dev
```

## Docs

| Document | Purpose |
|----------|--------|
| [ANCHOR.md](./docs/ANCHOR.md) | Product definition — the north star |
| [CONSTRAINTS.md](./docs/CONSTRAINTS.md) | Decision framework |
| [STATE.md](./docs/STATE.md) | Current position + session log |

## License

MIT

---

Built by Jaymin Chang — MSCS @ Northeastern Vancouver
