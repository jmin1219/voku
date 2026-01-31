# Review Queue Design (v0.2)

> Human-in-the-loop confirmation before data persists.

## Core Insight

Both fitness and finance have the same pattern:
- Extract structured data (from image or PDF)
- Some fields are "known" (mapped to canonical names)
- Some fields are "unknown" (need human decision)
- Human confirms → data saves

**One UI, multiple domains.**

---

## The Review Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Upload    │────▶│   Extract   │────▶│   Review    │────▶│    Save     │
│  (img/pdf)  │     │  (backend)  │     │   Queue     │     │  (confirm)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ For each unknown │
                                    │ • Confirm as new │
                                    │ • Map to existing│
                                    │ • Skip/ignore    │
                                    └─────────────────┘
```

---

## Domain Examples

### Fitness Unknown
```
Extracted: "Avg HR" → 143 bpm
Status: UNKNOWN (not in variable registry)

Actions:
[Add as new variable]  [Map to "Average Heart Rate"]  [Skip]
```

### Finance Unknown
```
Extracted: "DOORDASHPRINKLECHIC" → -$68.53
Status: UNKNOWN (not in merchant patterns)

Actions:
[Create merchant: DoorDash]  [Map to existing merchant]  [Skip]
      └─ Category: Delivery
      └─ Vendor: Prinkle Chic
```

---

## Data Model

### ReviewItem (domain-agnostic)

```typescript
interface ReviewItem {
  id: string;
  domain: "fitness" | "finance";
  status: "pending" | "confirmed" | "skipped";
  
  // What was extracted
  raw_value: string;
  
  // Domain-specific payload
  payload: FitnessPayload | FinancePayload;
  
  // User's decision (after review)
  resolution?: {
    action: "add_new" | "map_existing" | "skip";
    target?: string;  // canonical name or merchant to map to
  };
}
```

### FitnessPayload
```typescript
interface FitnessPayload {
  variable_name: string;
  value: string;
  unit?: string;
  suggested_canonical?: string;  // fuzzy match suggestion
}
```

### FinancePayload
```typescript
interface FinancePayload {
  raw_description: string;
  amount: number;
  date: string;
  suggested_merchant?: string;
  suggested_category?: string;
}
```

---

## API Endpoints (New for v0.2)

### POST /review/submit
Submit extraction results for review.

Request:
```json
{
  "domain": "fitness",
  "source": "image_upload",
  "items": [
    {"raw_value": "Avg HR", "payload": {...}, "status": "unknown"},
    {"raw_value": "Duration", "payload": {...}, "status": "known"}
  ]
}
```

Response:
```json
{
  "review_id": "abc123",
  "pending_count": 1,
  "known_count": 1
}
```

### GET /review/{review_id}
Get review session with all items.

### POST /review/{review_id}/resolve
Resolve a single item.

```json
{
  "item_id": "xyz",
  "action": "add_new",
  "canonical_name": "Average Heart Rate"
}
```

### POST /review/{review_id}/confirm
Confirm entire session → triggers save to domain storage.

---

## UI Components

### 1. Upload Panel
- Drag/drop image (fitness) or PDF (finance)
- Domain auto-detected or user-selected
- "Extract" button

### 2. Review List
- Shows all extracted items
- Known items: green checkmark, collapsed
- Unknown items: yellow warning, expanded with actions
- Bulk actions: "Confirm All Known", "Skip All Unknown"

### 3. Resolution Modal
For unknown items:
- Text field for new canonical name
- Dropdown of existing options (fuzzy-matched)
- Domain-specific fields (category for finance)

### 4. Confirmation Summary
Before final save:
- Count of items to save
- Count skipped
- "Save" / "Cancel"

---

## Implementation Order

1. **Fitness first** — simpler payload, existing backend
2. **Finance second** — add once patterns proven
3. **Polish** — bulk actions, keyboard shortcuts, mobile

---

## Why This Design

| Alternative | Why Not |
|-------------|---------|
| Two separate UIs | More code, less interview story |
| Auto-save everything | Loses human oversight, data quality suffers |
| CLI-only review | Defeats "personal AI" vision, bad UX |

**Interview angle:** "I designed a domain-agnostic review system. Adding a new data domain means implementing one interface, not building a new UI."

---

## Open Questions

- [ ] Persist review sessions to disk or memory-only?
- [ ] How long to keep unconfirmed sessions?
- [ ] Fuzzy matching threshold for suggestions?
