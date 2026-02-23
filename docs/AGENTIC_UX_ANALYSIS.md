# Voku — Agentic UX Analysis & Integration Plan

**Created:** 2026-02-22
**Status:** Research-backed analysis informing Phases B-D build decisions.
**Sources:** Deep research report (Feb 22), codebase review, DESIGN_STRATEGY.md cross-reference.

---

## Three User Workflows

### Workflow 1: Daily Conversation Session

The user opens Voku to think through something.

1. **Open** → Phase space ambient, chat ready for input
2. **Type** → Subtle ambient resonance in phase space (peripheral)
3. **Submit** → Processing state (collective ripple), input shows thinking indicator
4. **Response streams** → Chat fills, retrieval metadata lights up phase space, ActiveSummary updates
5. **Glance at phase space** → See which past beliefs the system used. Expand ActiveSummary for details. Trust builds.
6. **Continue** → 2-5 more exchanges. Phase space is living context window.
7. **Done** → "+ new" or close. Extraction runs. Birth animation shows knowledge growing.

**Current gaps:**
- Single-line `<input>` — needs multiline Textarea for thinking-out-loud paragraphs
- No processing state between submit and response
- Layout mode is a cycling button (can't directly pick dimension mode)
- No keyboard shortcuts (Enter send, Cmd+N new, Escape collapse)
- ActiveSummary not discoverable (thin bar, unclear purpose)

### Workflow 2: Explore & Reflect

The user opens Voku to look, not talk. Surveying accumulated knowledge.

1. **Open** → Eye goes to phase space, not input
2. **Orbit and zoom** → Spatial exploration of clusters, density, gaps
3. **Hover nodes** → Labels appear, read propositions, build mental map
4. **Click a node** → **Currently broken — no click handler.** Should open detail: full text, provenance, dimension, confidence
5. **Switch layout modes** → Dimension mode for self-model, time mode for temporal arc
6. **Trigger conversation from exploration** → Click node → inject into chat as reference → ask about it

**Current gaps:**
- No node click → detail view (only hover shows truncated label)
- No phase space → chat direction (interaction is one-way)
- Layout cycling hostile to exploration (must pass through irrelevant modes)
- No zoom-to-node on click
- No self-model overview panel

### Workflow 3: Demo Visitor

Hiring manager clicks URL. 60-120 seconds of attention.

1. **Land** → See populated phase space (400 nodes, breathing). Chat secondary. 3D is the hook.
2. **Instinct** → Drag to orbit, scroll to zoom. Must be instant and smooth.
3. **Discover nodes** → Hover reveals beliefs. First conceptual click: "these are extracted from conversation."
4. **Discover modes** → Click through layout modes. Dimension = user model. Time = temporal arc.
5. **Try typing** → Send a message. Response streams. New nodes born. **Wow moment.**
6. **Understand** → Leave knowing: "Temporal knowledge graph from conversation with visible self-model."

**Current gaps:**
- No onboarding hints (visitor doesn't know they can orbit/zoom/hover)
- Layout switcher too subtle (small cycling button)
- No "what is this?" framing
- Chat panel takes 30% but isn't the star for demo

---

## UI Library Strategy: shadcn/ui Adoption

### Current state
- shadcn already set up: Radix primitives, CVA, clsx, tailwind-merge installed
- 8 components exist in `/components/ui/`: button, card, input, dialog, badge, table, label, alert-dialog
- **None are used.** All components hand-styled with inline CSS.

### Components to add

**Workflow 1 (Conversation):**
- Textarea — auto-growing, Enter sends, Shift+Enter newlines
- ScrollArea — consistent styled scrollbar for chat
- Separator — conversation boundaries
- Tooltip — on all controls

**Workflow 2 (Exploration):**
- Popover or HoverCard — node detail on click
- Tabs or ToggleGroup — direct layout mode selection
- Sheet — slide-out self-model panel

**Workflow 3 (Demo):**
- Tooltip — onboarding hints
- Badge (exists) — type/dimension labels in detail view

**Total: ~6 new components** via `npx shadcn@latest add <component>`

### Theme integration
- tokens.css maps to shadcn CSS variables
- Chat panel: shadcn + Tailwind utilities
- 3D components (DataNode, Scene): stay inline (Three.js land)
- Dividing line: Workspace.tsx layout

---

## Research Validations (keep as-is)

- 30/70 chat/phase-space ratio ✓
- Goodhart's Law mitigations (no scores, descriptive mirrors, Wrapped-style) ✓
- Retrieval IDs as trust signal (server IDs primary) ✓

## Research Validations (revised Feb 22 Session 13)

- ~~Breathing animation parameters (3-6s period, ±3-8% amplitude)~~ → Deprioritized. Breathing is lowest-priority animation. Visual life comes from retrieval response, birth, and mesh connectivity.
- ~~Cluster shell removal~~ → Cluster shells replaced by **ambient k-NN mesh** (Layer 1). Density of connectivity = cluster. Shells delete, mesh replaces.
- ~~No edges design statement~~ → **Reframed.** "No edges to curate" (ANCHOR) is a data architecture principle, not a visual principle. Three layers of perceptible connection now defined. See DESIGN_STRATEGY.md Principle 2.

## Research Additions (integrate)

- **Three edge layers** — ambient mesh (k-NN, always present), retrieval connections (dynamic, during response), dimension connections (self mode radials). See DESIGN_STRATEGY.md Principle 2.
- **Retrieval response sequence** as primary "alive" signal — replaces processing state pulse. Edges light up between retrieved nodes, camera focuses, edges fade after response.
- **InstancedMesh + edge rendering** moved to Phase B (demo reliability + edge count)
- **Governor pattern** for birth animation (scale from 0, 70% opacity → full over 5s) with mesh edges connecting to neighbors
- **Chat collapse / theater mode** (floating input bar)
- **Bidirectional linking** (node click → chat context chip)
- **Self-model panel** (anti-ChatGPT-dossier, transparent)
- **Semantic zoom** three tiers (points → labels → full content by camera distance)
- **Timeline companion view** (horizontal strip, not card list)
- **Onboarding hints** for demo visitors
- **Chat panel decomposition** — ChatHeader, ChatMessages, ChatInput as semantic regions
- **Footer legend migrates to phase space** — chat panel becomes purely conversational
- **Auto-growing Textarea** (Claude-style) replaces single-line input

## Explicitly Skipped

- AG-UI protocol (overengineered for solo project)
- WebGPU (post-demo, bleeding edge risk)
- zustand migration (works as-is, refactor post-demo)
- Lasso selection (not in 60s demo narrative)
- Wrapped-style reflection (needs accumulated data, post-demo)
- Vercel AI Elements (shadcn adoption is enough)

---

## Revised Build Sequence (Updated Feb 22, Session 13)

Key revision: Three edge layers replace "no edges" visual approach. Breathing deprioritized. Phase C reordered by demo narrative priority. See DESIGN_STRATEGY.md for full rationale.

### Phase B: Chat + Rendering + Edge Foundation (3 sessions)

**B1: Chat panel redesign + shadcn adoption**
- Decompose ChatPanel.tsx into ChatHeader, ChatMessages, ChatInput
- Pull shadcn Textarea, ToggleGroup, ScrollArea, Tooltip
- Auto-growing Textarea (Enter sends, Shift+Enter newlines, Claude-style vertical growth)
- ToggleGroup for direct mode selection (replaces cycling button)
- Tooltips on all header controls
- Remove footer legend from chat (moves to phase space in B3)

**B2: InstancedMesh + edge rendering system**
- InstancedMesh for all nodes (single draw call)
- Per-instance attributes: position, color, scale, opacity, glowIntensity
- THREE.LineSegments with BufferGeometry for edges (ambient + retrieval as separate geometries)
- Instanced raycasting + distance-culled Html labels
- Layout position transitions (lerp ~0.8s)
- Simplify or remove breathing
- Backend: k-NN edge list in `compute_projection()` return

**B3: Three edge layers + spatial clarity**
- Layer 1 (structural mesh): ambient k-NN edges. Replaces ClusterShell.tsx.
- Layer 2 (retrieval connections): bright edges between retrieved nodes during response. Primary "alive" signal.
- Layer 3 (dimension connections): radial edges to centroids in self mode + gravity.
- Legend overlay on phase space. Density labels. Layer visibility per mode.

### Phase C: Interaction + Polish (3 sessions, demo-priority order)

**C1: Demo-critical (completes 60-second narrative)**
- Birth animation + mesh edge connection to neighbors
- Extraction count notification
- Onboarding hints + demo context label

**C2: Exploration depth (beyond 60 seconds)**
- Node click → Popover detail + camera focus
- "Ask about this" → chat context chip

**C3: Workflow 2 (explore & reflect)**
- Timeline strip + self-model Sheet panel
- Dimension narrative labels + theater mode

### Phase D: Demo Deployment (2 sessions)
1. Synthetic persona (20 sessions, 300-400 propositions)
2. Dockerfile + Railway + demo mode + pre-seeded voku.db

**Total: ~8 sessions → before Mar 31 demo**
**Minimum viable demo: through C1.** C2-C3 add depth but narrative is complete after C1.

---

## References

- Artium.ai medical platform user testing — chat dominates attention
- ElevenLabs UI Orb — Three.js/R3F state machine pattern
- AuraOrb (Georgia Tech) — progressive turn-taking 5-stage model
- Calm Tech Institute 81-point certification (May 2024)
- ChatGPT memory reverse-engineering (Khemani Sep 2025, Willison May 2025)
- Transluce AI transparency principle (Steinhardt Nov 2025)
- Algorithmic Mirror project (2025) — spatial maps enhance algorithmic literacy
- Akpan & Shanker meta-analysis — 3D better for exploration, 2D for precise comparison
- Smashing Magazine AI design patterns (Friedman Jul 2025)
- Vercel AI Elements / shadcn AI components
- assistant-ui (YC) — composable AI chat primitives
- AG-UI protocol (CopilotKit Dec 2025)
