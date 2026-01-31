# Voku API Documentation

Base URL: `http://localhost:8000`

---

## Core Endpoints

### Health Check

`GET /health`

Returns API health status.

**Response:**
```json
{ "status": "healthy" }
```

---

## Fitness Domain

### Log Training Session

`POST /log/training/session`

Upload a workout screenshot to extract, normalize, and log fitness metrics.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `image` (file, required)

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sensitive` | boolean | `false` | If `true`, routes to local Ollama (data never leaves machine). Default uses Groq for speed. |

**Response:**
```json
{
  "filename": "indoor_cycle_summary.png",
  "parsed": {
    "workout_type": "Indoor Cycle",
    "variables": {
      "avg_heart_rate": { "value": "143", "unit": "bpm" },
      "distance": { "value": "21.56", "unit": "km" },
      "workout_time": { "value": "0:55:00", "unit": "hh:mm:ss" }
    }
  },
  "id": "a51ad949",
  "logged_to": "data/sessions/2026-01-23_17-36-10_a51ad949.json",
  "provider": "GroqProvider",
  "unknown_variables": ["workout_time", "distance"],
  "stats": {
    "matched": 1,
    "total": 3
  }
}
```

**Response Fields:**

| Field | Description |
|-------|-------------|
| `filename` | Original uploaded filename |
| `parsed` | Normalized metrics (canonical names where known, original where unknown) |
| `id` | Unique session identifier (8 chars) |
| `logged_to` | File path where session was saved |
| `provider` | AI backend used (`GroqProvider` or `OllamaProvider`) |
| `unknown_variables` | Variable names not in registry (need user confirmation) |
| `stats.matched` | Variables that matched registry |
| `stats.total` | Total variables extracted |

**Errors:**
- `422` — No image provided
- `503` — Vision API unavailable

**Examples:**

```bash
# Default (Groq cloud, faster)
curl -X POST http://localhost:8000/log/training/session \
  -F "image=@data/test_images/apple_fitness/indoor_cycle_summary.png"

# Sensitive mode (local Ollama, private)
curl -X POST "http://localhost:8000/log/training/session?sensitive=true" \
  -F "image=@data/test_images/apple_fitness/indoor_cycle_summary.png"
```

---

### Get Training Sessions

`GET /fitness/sessions`

Retrieve training session history.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Maximum sessions to return |
| `offset` | integer | 0 | Skip N sessions |

**Response:**
```json
{
  "sessions": [
    {
      "id": "a51ad949",
      "created_at": "2026-01-23T17:36:10",
      "workout_type": "Indoor Cycle",
      "variables": {
        "avg_heart_rate": { "value": "143", "unit": "bpm" }
      }
    }
  ],
  "total": 15
}
```

**Example:**

```bash
curl http://localhost:8000/fitness/sessions?limit=10
```

---

## Finance Domain

### Import Transactions

`POST /finance/import`

Upload a bank statement PDF to extract and categorize transactions.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (PDF file, required)

**Response:**
```json
{
  "transactions_imported": 20,
  "new_merchants": 3,
  "file": "CAD_Toss.pdf"
}
```

**Response Fields:**

| Field | Description |
|-------|-------------|
| `transactions_imported` | Number of transactions extracted |
| `new_merchants` | New merchants added to categorization system |
| `file` | Original filename |

**Errors:**
- `422` — No file provided or invalid PDF
- `500` — Parsing error

**Example:**

```bash
curl -X POST http://localhost:8000/finance/import \
  -F "file=@data/finance/imports/CAD_Toss.pdf"
```

---

### List Transactions

`GET /finance/transactions`

Retrieve transaction history with optional filtering.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 100 | Maximum transactions to return |
| `offset` | integer | 0 | Skip N transactions |
| `category` | string | — | Filter by category |
| `start_date` | string | — | ISO date (YYYY-MM-DD) |
| `end_date` | string | — | ISO date (YYYY-MM-DD) |

**Response:**
```json
{
  "transactions": [
    {
      "id": 1,
      "date": "2026-01-15",
      "description": "STARBUCKS CAFE",
      "amount": -5.47,
      "currency": "CAD",
      "merchant": "Starbucks",
      "category": "Dining"
    }
  ],
  "total": 150
}
```

**Examples:**

```bash
# All transactions
curl http://localhost:8000/finance/transactions

# Filter by category
curl "http://localhost:8000/finance/transactions?category=Dining"

# Date range
curl "http://localhost:8000/finance/transactions?start_date=2026-01-01&end_date=2026-01-31"
```

---

### Monthly Summary

`GET /finance/summary`

Get spending breakdown by category for a specific month.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `month` | string | Yes | Format: YYYY-MM |

**Response:**
```json
{
  "month": "2026-01",
  "total_spent": 1247.56,
  "categories": [
    {
      "category": "Dining",
      "amount": 342.18,
      "count": 15,
      "percentage": 27.4
    },
    {
      "category": "Groceries",
      "amount": 287.94,
      "count": 8,
      "percentage": 23.1
    }
  ]
}
```

**Response Fields:**

| Field | Description |
|-------|-------------|
| `month` | Month in YYYY-MM format |
| `total_spent` | Sum of all spending (absolute value) |
| `categories[].category` | Category name |
| `categories[].amount` | Total spent in category |
| `categories[].count` | Number of transactions |
| `categories[].percentage` | Percentage of total spending |

**Example:**

```bash
curl "http://localhost:8000/finance/summary?month=2026-01"
```

---

## Variable Registry (Planned - v0.2)

### List Variables

`GET /registry/variables`

Returns all known canonical variables from the registry.

**Response:**
```json
{
  "variables": {
    "avg_heart_rate": {
      "display": "Avg Heart Rate",
      "aliases": ["avg_hr", "Avg HR", "heart_rate_avg"],
      "unit": "bpm",
      "count": 5
    }
  }
}
```

### Add Variable

`POST /registry/variables`

Add a new canonical variable to the registry.

**Request:**
```json
{
  "name": "max_power",
  "display": "Max Power",
  "unit": "watts"
}
```

### Add Alias

`POST /registry/variables/{name}/aliases`

Add an alias to an existing canonical variable.

**Request:**
```json
{
  "alias": "Peak Power"
}
```

---

## Data Storage

### Fitness Sessions

Sessions saved to: `data/sessions/{date}_{time}_{id}.json`

```json
{
  "id": "a51ad949",
  "created_at": "2026-01-23T17:36:10.123456",
  "workout_type": "Indoor Cycle",
  "variables": {
    "avg_heart_rate": { "value": "143", "unit": "bpm" },
    "distance": { "value": "21.56", "unit": "km" }
  }
}
```

### Finance Database

SQLite database at: `data/voku.db`

**Schema:**
- `transactions` — Transaction records with merchant and amount
- `merchants` — Known merchants with categorization
- `categories` — Spending categories
- `merchant_patterns` — LLM-learned categorization rules

### Variable Registry

Registry stored at: `data/registry/variables.json`

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

| Field | Description |
|-------|-------------|
| `display` | Human-readable name |
| `aliases` | Alternative names that map to this canonical name |
| `unit` | Expected unit of measurement |
| `count` | Number of times this variable has been observed |

---

## Error Responses

All endpoints use standard HTTP status codes:

| Code | Meaning |
|------|---------|
| `200` | Success |
| `422` | Validation error (missing or invalid parameters) |
| `500` | Server error |
| `503` | External service unavailable (e.g., AI provider) |

Error response format:
```json
{
  "detail": "Error message here"
}
```
