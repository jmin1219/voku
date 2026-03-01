# Voku — Interaction Design

**Created:** 2026-02-22
**Status:** Living document. How the system feels during use — the conversational lifecycle, visual vocabulary, and interaction patterns.
**Derived from:** Duality theory analysis (De Haro & Butterfield 2025), GEB synthesis (Hofstadter), immersive UI/UX research report, Ars Contexta competitive analysis, interaction design session (Feb 22).
**Nature:** This is the *feel* document. ANCHOR.md defines what Voku is. VISION.md explains why. DESIGN_STRATEGY.md maps the visual system. This document specifies what happens moment-to-moment when a human uses Voku.

---

## The Core Sensation: Co-Cognition

Voku should feel like thinking alongside someone who knows you — not a tool that processes your input, but an instrument that thinks *with* you and lets you see the thinking happen. The distinction:

- **ChatGPT:** talking to a stranger every time
- **Claude with memory:** talking to someone who read your file before the meeting
- **Voku:** talking to someone who knows you and is visibly thinking alongside you

The word is **co-cognition**. The phase space externalizes the system's understanding in real time. The user doesn't just get better responses — they *watch* the system connect what they're saying to what it already knows.

---

## The Seven Moments of Conversation

Every exchange has seven distinct moments. Each has specific visual behavior across both panels.

### Moment 1: Idle / Arrival

User opens Voku. The phase space breathes. Last conversation visible in chat.

| Surface | Behavior |
|---------|----------|
| Phase space | Ambient breathing (existing). Slow camera drift. Edges at base opacity. |
| Chat panel | Last conversation loaded. Input empty. |
| Bridge | None. Panels are independent. |

**Design reference:** Fish tank. Ambient presence. Non-demanding.

### Moment 2: Focus / Intention

User clicks the textarea.

| Surface | Behavior |
|---------|----------|
| Phase space | Breathing slows slightly. Camera drift stops. Edges dim to uniform low opacity. The space is *listening*. |
| Chat panel | Conversation history dims to opacity 0.6 (CSS transition, 300ms). Input area brightens. |
| Bridge | None yet. |

**Design reference:** The Witness — world quiets when you approach a puzzle panel.

### Moment 3: Mid-Message / Typing

User is mid-braindump. Words flowing.

| Surface | Behavior |
|---------|----------|
| Phase space | **Keyword glow (debounced 500ms).** Client-side scan of textarea value against node labels. Matching nodes increase emissive gently (lerp over 300ms). As user types different words, different nodes warm and cool. No animation — just luminance shift. |
| Chat panel | Text flows normally. Optional: recognized keywords get faint underline matching cluster color (Level 2, demo scope). |
| Bridge | Peripheral awareness only. The user should NOT look at the phase space during typing. But if they glance, they see it responding. |

**Implementation:** `useEffect` with 500ms debounce on textarea value. String matching against node labels (case-insensitive). Update a `Set<nodeId>` read by `useFrame` to adjust InstancedBufferAttribute emissive values. ~20 lines.

**Design reference:** Baba Is You — words change the world. Mini Metro — stations highlight when they need attention.

### Moment 4: Message Sent

The moment between sending and the system responding.

| Surface | Behavior |
|---------|----------|
| Phase space | **Retrieval activation cascade.** Backend returns retrieved node IDs as a separate SSE event BEFORE the response stream begins. Nodes activate in a staggered cascade (most similar first, then neighbors). Edges between activated nodes pulse. Duration: 500ms-1s before response starts streaming. |
| Chat panel | User message appears. Typing indicator or subtle "thinking" state. |
| Bridge | **This is the key co-cognition moment.** The user watches the phase space light up and thinks: "It's connecting what I said to what it already knows." |

**Backend requirement:** Emit retrieval results as separate SSE event:
```
event: retrieval
data: {"nodeIds": [42, 87, 103, 256, 301]}
```
~10-15 lines in chat endpoint. After retrieval runs, before streaming starts.

**Design reference:** The feeling of someone's eyes lighting up with recognition when you mention something they know about.

### Moment 5: Response Streaming

AI response streams token by token.

| Surface | Behavior |
|---------|----------|
| Phase space | Retrieved nodes stay activated (elevated emissive). If the response mentions concepts not in the retrieval set, those nodes can get a secondary, dimmer activation. Edges between all activated nodes visible. |
| Chat panel | Response streams. Optional: when response references prior context, subtle side-border or margin icon on that paragraph (post-demo). |
| Bridge | Stable. The activated constellation holds while the user reads. |

### Moment 6: Extraction / Birth

Response complete. Extraction runs on the full exchange.

| Surface | Behavior |
|---------|----------|
| Phase space | **New nodes materialize with birth animation.** Scale from 0 → 1.0 via spring physics (mass 1, tension 170, friction 26). Initial color warmer/brighter than settled nodes ("freshly born" state). Warm glow cools to cluster color over 15-20s. Position: UMAP-computed from embedding. |
| Chat panel | **Extraction summary appears below AI response.** Collapsed by default: "✦ 2 new concepts · 1 connection strengthened · linked to 4 existing ideas." Expandable to show proposition texts. |
| Bridge | **Optional extraction trail (demo scope):** brief particle trail from message position → across divider → new node birth position. Visible for ~1s. Establishes causal link: "your words became that node." |

**Design reference:** Gorogoa — alignment between panels reveals connections.

### Moment 7: Settlement

Extraction complete. System returns to idle.

| Surface | Behavior |
|---------|----------|
| Phase space | UMAP recomputes if needed. Nodes drift to final positions (spring physics, 1-2s). New edges form if k-NN recalculated. Birth glow cools. Breathing resumes at normal rate. |
| Chat panel | Extraction summary persists until next message. History restores to full opacity. |
| Bridge | Dissolves. Panels return to independent ambient state. |

**The key property:** The phase space looks *slightly different* after every exchange. A few more nodes. A few brighter edges. A slightly denser region. Over ten conversations, the user can see where their thinking has been.

---

## Visual Vocabulary of Understanding

Five visual signals communicate distinct aspects of the system's relationship to the user's knowledge:

| Signal | Visual | Meaning | When |
|--------|--------|---------|------|
| **Recognition** | Existing node brightens (emissive increase) | "I know about this concept" | Mid-message keyword match or retrieval activation |
| **Connection** | Edges pulse between activated nodes; cross-cluster arcs for distant concepts | "These things relate, and I know they relate because you've told me about both" | Retrieval activation (Moment 4) |
| **Novelty** | New node birth animation — spring scale-in, warm gold glow cooling to cluster color | "You just taught me something I didn't have before" | Post-extraction (Moment 6) |
| **Updating** | Existing node briefly flashes or subtly shifts position | "What you just said changed how I weight something I already knew" | Dimension score update (post-demo) |
| **Surprise** | Bright arc across spatial distance; edge visually distinct from local connections | "You probably didn't realize these are connected, but they are" | Cross-domain retrieval activation |

---

## Message Block Highlighting

After a message is sent, phrases matching existing nodes receive subtle background highlights tinted to their cluster color. A braindump touching three domains shows three color regions in the message text.

**Interaction on hover:**
- Highlighted phrase → corresponding node pulses in phase space
- Tooltip: "Connected to N related concepts"
- Click: injects concept as focus filter on phase space

**Implementation:** Piggybacks on retrieval results. Retrieved proposition IDs → map to node labels → scan user message for matches → apply `<span>` with cluster color background at low opacity.

---

## Node Creation Lifecycle

### Principle: Visible Birth, No Confirmation

Extraction is **visible but not gated**. The user sees nodes being born. They don't approve them. They can dismiss afterward if wrong.

**Why no confirmation:** The moment you ask "should I add this?" you've turned conversation into data entry. You've added a layer. Zero-cost externalization requires invisible extraction. The knowledge graph builds as a side effect of conversation.

**Why visible:** The user needs a mental model of what's in the graph. Trust requires seeing the system build understanding, not just receiving better responses.

**Why not extract from user message alone:** User messages are often ambiguous ("the nutrition thing isn't working"). The AI response disambiguates. Extraction runs on the full exchange because the AI's response is itself a processing step.

**Exception — direct declarative statements:** "I've decided to switch from rowing to biking" is extractable without AI interpretation. The extraction system handles both: raw declarations from the user AND synthesized understanding from the exchange.

### Dismiss Pattern

- Click new node → popover has dismiss/delete button
- Node dissolves (spring scale to 0, fade out)
- Proposition soft-deleted (marked inactive, not removed from DB)
- Extraction summary in chat has per-item × for dismiss (secondary affordance)

### Manual Node Creation: No

The user should never manually add nodes to the phase space. If they want to add a concept, they say it in conversation. The chat IS the creation interface. The phase space is the read interface, not the write interface.

**Post-demo exception:** Users can merge, split, or rename extracted propositions through the phase space. This is curation, not creation.

---

## Phase Space Interactions

### Click → Popover (C2 scope)

Floating card near the node:
- Proposition text (the actual words)
- Relative timestamp ("3 days ago")
- Dimension tag
- Confidence level (qualitative: "deeply rooted" / "emerging" / "in tension")
- "Ask about this" button → injects concept into chat input
- Dismiss button (for newly created nodes)

### Hover → Neighborhood Reveal

Hovering a node brightens its k-NN neighbors and connecting edges. Shows local conceptual neighborhood without requiring a click.

### Bidirectional Hover Bridge

- Hover highlighted phrase in chat → pulse corresponding node in phase space
- Hover node in phase space → highlight corresponding phrases in recent messages
- Creates navigable bridge: chat indexes the space, space indexes the chat

### Layout Mode Transitions

When switching modes (cluster → dimension → time → type), nodes spring to new positions with staggered timing. Closest nodes first, ripple outward. 300ms stagger across the full cloud. Monument Valley pacing — deliberate, trackable cadence.

### Zoom → Level of Detail

- Far: simple spheres, no labels, ambient cloud
- Mid: labels appear on larger nodes, cluster structure clear
- Close: full labels on all visible nodes, dimension tags, popover available
- Implemented via Drei's `<Detailed>` or manual LOD in useFrame

---

## Implementation Priority Map

| Phase | Pattern | Effort | Impact |
|-------|---------|--------|--------|
| **B3** | Keyword glow (debounced mid-message) | ~20 LOC | Medium — space feels alive during typing |
| **B3** | Retrieval activation via SSE event | ~15 LOC backend, ~30 LOC frontend | **High** — the core co-cognition moment |
| **B3** | Edge pulse shader (uTime in fragment) | ~10 LOC | Medium — edges carry energy during retrieval |
| **B3** | Selective bloom (UnrealBloomPass + THREE.Layers) | ~50 LOC | **High** — single biggest visual upgrade |
| **C1** | Birth animation (spring scale-in + warm glow) | ~40 LOC | **High** — visible extraction is demo-critical |
| **C1** | Extraction summary in chat panel | ~30 LOC | Medium — textual complement to visual birth |
| **C1** | Message block highlighting (retrieval-based) | ~40 LOC | Medium — bridges the two panels |
| **C2** | Node popover (text, time, dimension, dismiss) | ~80 LOC | Medium — exploration depth |
| **C2** | Bidirectional hover bridge | ~60 LOC | Medium — navigable connection |
| **C2** | Extraction trail particle (message → node) | ~50 LOC | Medium — demo wow factor |
| **Post** | Layout mode staggered transitions | ~40 LOC | Low — polish |
| **Post** | Zoom-based LOD | ~30 LOC | Low — scalability |
| **Post** | Reweave pass (update old propositions) | Architecture | High — "Day 30" quality |

---

## Theoretical Grounding

### Duality Theory (De Haro & Butterfield 2025)

The phase space implements duality in the formal physics sense. Each layout mode (cluster, dimension, time, type) is a *model* — a specific representation that adds its own "specific structure" to the common core (the propositions and their geometric properties). The duality mapping is the re-projection. The common core theory is the user's evolving understanding. No single projection captures it. The manifold does.

The "same data, different projection, different structure" principle from ANCHOR.md is not a metaphor for duality — it IS duality. This gives Voku formal vocabulary: the projection engine implements duality transformations. The k-NN edges measure intrinsic topology (metric structure that persists regardless of projection). Emergence in the phase space (clusters, patterns, trajectories) follows the same logic as emergence in the Ising model — below a critical mass of propositions, the space is noise; above it, structure self-organizes.

### Strange Loops (Hofstadter, GEB 1979)

Voku creates a strange loop: the user generates data (conversation) → the system models the user (extraction + user model) → the user observes the model (phase space) → the observation changes what the user says → which changes the model. The user is simultaneously subject, object, and observer.

Making the model *visible* through the phase space is what closes the loop. Without visibility, Voku is a database with good retrieval. With visibility, it's an instrument for self-perception. Visibility is architecturally essential, not a UX choice.

The Gödelian constraint applies: formalizing "what counts as an insight" would either miss genuine insights (incompleteness) or hallucinate false ones (inconsistency). The phase space doesn't define insights — it makes structure visible. The user brings the interpretive capacity no formal system can fully capture. This division of labor is the architecturally correct response to incompleteness.

### Extended Mind (Clark & Chalmers 1998)

For the phase space to function as extended cognition, it must be: (1) reliably accessible — always visible, not behind a tab; (2) automatically endorsed — the user trusts it without checking; (3) directly influencing behavior — clicking a node does something.

---

## Competitive Note: Ars Contexta

Ars Contexta (Claude Code plugin, Feb 2026) generates markdown-based knowledge vaults from conversation. Their three-space architecture (self/notes/ops), 6Rs pipeline (Record→Reduce→Reflect→Reweave→Verify→Rethink), and seed-evolve-reseed lifecycle inform Voku's post-demo evolution.

**Key difference:** Ars Contexta is a text-only, agent-operated system. The human never sees the knowledge structure directly. Voku's phase space — real-time spatial visualization that reacts to conversation — is the fundamental differentiator. Their visualization is a viewer bolted onto a vault. Voku's visualization is the instrument itself.

**Ideas adopted for post-demo:**
- **Reweave pass:** When new propositions cluster near old ones, re-evaluate old dimension scores, merge duplicates, flag contradictions.
- **Seed-evolve-reseed lifecycle:** The user model should periodically re-derive, not just accumulate.
- **Kernel specification:** Formalize the 5-8 invariants that must hold for any Voku instance (every proposition has an embedding, every conversation has at least one extraction, context assembly retrieves within 200ms, etc.).