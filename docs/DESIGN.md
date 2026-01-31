# Voku Design

Multi-domain personal context architecture for AI-powered data extraction and analysis.

---

## Architecture Overview

Voku implements a **domain-extensible architecture** where domains (fitness, finance, career) are first-class concepts, not afterthoughts. The system is designed to handle N domains with consistent patterns for extraction, normalization, and storage.

```
┌────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐│
│  │   Fitness   │  │   Finance   │  │  Future Domains (N...)  ││
│  │    Pages    │  │    Pages    │  │                         ││
│  └─────────────┘  └─────────────┘  └─────────────────────────┘│
└────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    Router Layer                           │ │
│  │  /fitness/*  │  /finance/*  │  /registry/*  │  /health   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                            │                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                   Service Layer                           │ │
│  │                                                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │ │
│  │  │  Provider   │  │  Normalizer │  │  Domain Logic   │  │ │
│  │  │ Abstraction │  │  + Registry │  │  (Fitness, Fin) │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                      Storage Layer                              │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  JSON Sessions  │  │  SQLite DB   │  │ Variable Registry│ │
│  │  (Raw extracts) │  │ (Structured) │  │ (Normalization)  │ │
│  └─────────────────┘  └──────────────┘  └──────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

---

## Core Subsystems

### 1. Provider Abstraction

**Purpose:** Route AI workloads based on requirements (speed vs. privacy)

**Design Pattern:** Strategy pattern with environment-based selection

```python
class Provider(ABC):
    @abstractmethod
    async def vision(self, image_base64: str, prompt: str) -> str:
        pass

class GroqProvider(Provider):
    # Cloud-based, fast, free tier sufficient
    model = "llama-4-scout"
    
class OllamaProvider(Provider):
    # Local, private, no external API calls
    model = "llama3.2-vision"
```

**Routing Logic:**
```python
if sensitive or config.FORCE_LOCAL:
    provider = OllamaProvider()
else:
    provider = GroqProvider()
```

**Benefits:**
- Vendor switching without code changes
- Graceful degradation if cloud provider unavailable
- Privacy control at call site
- Mockable interface for testing

---

### 2. Variable Registry

**Purpose:** Name normalization across sessions (human-in-the-loop feedback)

**Problem:** Vision models extract inconsistent names
- "Avg HR" vs "Average Heart Rate" vs "avg_heart_rate"
- User shouldn't see duplicates or manually merge

**Solution:** Registry maps aliases → canonical names

```json
{
  "avg_heart_rate": {
    "display": "Avg Heart Rate",
    "aliases": ["avg_hr", "Avg HR", "heart_rate_avg"],
    "unit": "bpm",
    "count": 5
  }
}
```

**Flow:**
1. Extract variables from image
2. Check registry: known names → use canonical, unknown → flag
3. UI asks user: "Is 'Avg HR' the same as 'Average Heart Rate'?"
4. User decision → update registry
5. Future extractions use learned mapping

**Architecture:** Standard HITL (human-in-the-loop) pattern

---

### 3. Domain Separation

**Design:** Each domain has its own router, service layer, and storage

```
backend/
├── app/
│   ├── routers/
│   │   ├── fitness.py      # GET /fitness/sessions
│   │   └── finance.py      # POST /finance/import, GET /finance/transactions
│   ├── services/
│   │   ├── fitness/
│   │   │   └── [fitness-specific logic]
│   │   ├── finance/
│   │   │   ├── parser.py       # PDF extraction
│   │   │   ├── db.py           # SQLite operations
│   │   │   └── categorizer.py  # LLM categorization
│   │   └── [shared services]
```

**Benefits:**
- Clean separation of concerns
- Domain experts can own their modules
- Adding new domains doesn't touch existing code
- Independent testing per domain

---

### 4. Two-Layer Storage Model

**Operational Layer** (voku.db - SQLite)
- Structured, queryable records
- Domain-specific schemas
- `training_sessions`, `transactions`, `merchants`, etc.

**Knowledge Layer** (ChromaDB - v0.3)
- Unstructured concepts, patterns, insights
- Semantic search across sessions
- "Show me workouts where I felt strong" → retrieves relevant sessions

**Rationale:**
- Operational queries need SQL joins and aggregations
- Knowledge queries need semantic similarity
- Don't conflate the two - each tool optimized for its use case

---

## Data Flow Examples

### Fitness: Image Upload

```
1. User uploads workout screenshot
2. Router → Provider (Groq or Ollama)
3. Vision API extracts structured data
4. Parser validates JSON structure
5. Normalizer checks registry
   → Known variables: use canonical names
   → Unknown variables: flag for user confirmation
6. Storage saves:
   - Raw JSON to data/sessions/
   - Stats to operational DB (future)
7. Response includes:
   - Parsed data
   - Unknown variables list
   - Provider used
```

### Finance: PDF Import

```
1. User uploads bank statement PDF
2. Parser extracts transactions (date, amount, description)
3. For each transaction:
   - Check merchants table
   - If new merchant → LLM categorization
   - Store categorization pattern for reuse
4. Bulk insert to SQLite
5. Response includes:
   - Transactions imported count
   - New merchants learned
```

---

## Design Decisions

### Why Provider Abstraction?

**Not premature abstraction.** Enables:
- Testing without API calls
- Graceful degradation
- Privacy control
- Vendor lock-in prevention

Industry-standard pattern for LLM-agnostic systems.

### Why No LangChain?

**Strongly defensible.** 
- 45% of developers who try LangChain never use it in production (2025 survey)
- Direct API calls provide full observability
- Debugging LangChain chains is harder than debugging HTTP requests
- No framework lock-in

Trade short-term convenience for long-term control.

### Why SQLite?

**Single-user local-first design.**
- Configured with WAL mode for concurrency
- Handles typical use case (one person logging data)
- Migration path to PostgreSQL documented if needed
- Zero ops overhead during development

### Why ChromaDB?

**Appropriate for portfolio scale.**
- Local-first, no external dependencies
- Simple Python API
- Production scaling → Qdrant or Pinecone

Shows architectural maturity: choosing tools for appropriate scale.

### Why Mixed-Theme Design?

**Evidence-based decision.**
- Piepenbrock (2014): 20-26% reading speed advantage for positive polarity (light backgrounds)
- Transaction tables = text-heavy → light mode
- Metrics dashboards = data visualization → dark mode (Helmholtz-Kohlrausch effect)

Content-driven theming based on function, not aesthetic preference.

---

## Testing Strategy

### Current Coverage
- 64 tests across 6 modules
- Parser, normalizer, registry, finance (parser, db, categorizer)

### Target Pyramid
```
     /\
    /E2E\      5-10%  - Full user flows
   /──────\
  /Integ  \    20-30% - API + DB interactions
 /─────────\
/   Unit    \  60-70% - Business logic
/────────────\
```

### Gaps to Address (v0.2.5)
- Error path testing (what if LLM fails?)
- LLM mocking (don't call real APIs in tests)
- Provider/router/storage unit tests
- Integration tests for full pipelines

---

## Security & Privacy

### Data Handling
- Sensitive mode forces local Ollama processing
- No telemetry, analytics, or usage tracking
- User data never leaves machine unless explicitly routed to Groq

### API Security (Future)
- Health checks for monitoring
- Request ID middleware for tracing
- Structured JSON logging for debugging
- Rate limiting for production deployment

---

## Scalability Considerations

### Current Design (Single User)
- SQLite with WAL mode
- JSON file sessions
- No auth, no multi-tenancy

### Production Migration Path
- SQLite → PostgreSQL for multi-user
- Add authentication (JWT)
- Containerize with Docker
- Deploy to Railway / Hugging Face Spaces
- Add Redis for caching

**Timeline:** Docker deferred to May 2026. Live demo prioritized for March 31 (hiring managers review <2 min).

---

## Future Enhancements

### v0.2 (In Progress)
- UI review flow for unknown variable confirmation
- Complete all 6 frontend pages

### v0.2.5 (Production Signals)
- Health check endpoints
- Structured logging with request IDs
- Error path testing

### v0.3 (Semantic Search)
- ChromaDB integration
- Session summarization → embedding
- Search endpoint for natural language queries

### v1.0 (Production)
- Multi-user support
- Authentication
- Deployed demo
- Comprehensive documentation

---

## Interview Defense Points

**"Why this architecture?"**
- Domain extensibility from day one, not bolted on
- Production-ready patterns (provider abstraction, HITL feedback, testing pyramid)
- Local-first privacy respects user data

**"Why no frameworks?"**
- FastAPI: minimal, standard, widely adopted
- No LangChain: direct control, easier debugging
- React without heavy state management: premature for current scale

**"What would you change?"**
- Add observability infrastructure earlier (health checks, logging)
- Mock LLM calls in tests from day one
- Implement hybrid embedding strategy for better retrieval

**"Hardest technical decision?"**
- Schema-free extraction vs. locked schemas
- Discovery phase benefits from flexibility
- Production needs validation and constraints
- Registry pattern is the bridge: learn structure, then lock it

---

See [STATE.md](../STATE.md) for current implementation status and [API.md](./API.md) for endpoint documentation.
