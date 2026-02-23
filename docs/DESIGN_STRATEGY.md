# Voku — Design Strategy

**Created:** 2026-02-21
**Status:** Living document. Frontend design philosophy, competitive positioning, and demo strategy.
**Derived from:** Market research (Feb 21), ANCHOR.md, THEORY.md, seven-domain analysis.

---

## Positioning

**Market gap:** No consumer product combines temporal knowledge graphs from conversation + visible user modeling across dimensions + 3D phase-space visualization. Kin comes closest on user modeling. Obsidian leads on graph visualization. Zep/Graphiti exists as developer infrastructure for temporal KGs. The full Voku concept has zero direct competitors.

**Cautionary precedents:** Dot (shut down Oct 2025, ~24.5K users despite "hundreds of thousands" claim), Limitless (acquired by Meta Dec 2025, stranding users), Pi (gutted by Microsoft acqui-hire Mar 2024). Pattern: cloud-dependent companion AI is fragile, data portability matters, clear interaction model beyond "chat with me" is essential for retention.

**Survivors' pattern:** Kin (on-device), Obsidian (local-first, 2000+ plugins), Granola ($43M Series B, anchored to meetings workflow). Anchor AI to a specific workflow. Voku's anchor is conversation.

---

## Design Philosophy: Ecology as Substrate, Phase Space as Frame

The phase space is a living knowledge ecology — not a scatter plot, not a knowledge graph, not a dashboard. Five principles govern all frontend decisions:

### 1. The Space Breathes

Nodes have life cycles: born (extraction), growing (evidence accumulation), breathing (idle), dimming (temporal decay). Breathing communicates confidence state from the exhale service:
- **High confidence (≥0.7):** Slow, deep breath (±8%, 6s period). Settled knowledge.
- **Low confidence (<0.4):** Faster, shallower breath (±3%, 3s period). Uncertain.
- **Conflicted:** Irregular rhythm. Tension.

Visual hierarchy at rest driven by `dimensionRelevance`:
- Anchor nodes (>0.7): scale 0.18-0.22, low roughness, catch light
- Body nodes (0.3-0.7): scale 0.10-0.16, standard material
- Dust (<0.3 or unassigned): scale 0.04-0.08, high roughness, matte

Soft halo on every node (opacity 0.02-0.06). No hard edges.

**Calm technology alignment:** Phase space is ambient presence — peripheral, alive, non-demanding. Moves to center of attention only when user engages.

### 2. Proximity Is the Relationship

No edges. No cluster shells. Closeness IS the relationship. UMAP positions encode semantic proximity. The absence of explicit edges is a design statement: meaning lives in topology, not links.

Density = cluster. No container needed. Floating ambient labels near density centers (very low opacity, camera-distance gated).

**Pair with 2D accessible view** from day one: timeline or card list as companion to 3D. The 3D is the "wow," the 2D is the "I can use this."

### 3. Attention Reshapes the Landscape

Server-retrieved IDs are the PRIMARY glow signal. Client-side keyword matching is secondary "ambient resonance" at most. This is a trust signal: bright = Claude is actually using this proposition.

Future: retrieved nodes pull toward camera slightly, non-retrieved push back. Gain control visualization — the task belief signal reconfiguring knowledge geometry.

### 4. Dimensions Are Regions, Not Categories

Dimension mode uses gravitational pull toward dimension centroids. High-relevance nodes pull close. Low-relevance stay near semantic position. Unassigned drift to periphery.

**Critical framing: narrative, not numerical.** Dimension anchors show qualitative descriptors ("deeply rooted," "emerging," "in tension"), NOT confidence scores. Raw numbers stay in backend. Visualization communicates through size, color saturation, breathing rate.

Color bleeding: nodes with dimensionRelevance < 0.6 blend toward neutral stone. Saturated centers, desaturating edges. Color field with gradient boundaries.

**Goodhart's Law mitigation:**
- No progress bars, streak counts, or leaderboards
- Descriptive mirrors, not achievement metrics
- Periodic reflection (Wrapped-style) over constant dashboard
- Informational framing ("You've been exploring X") not controlling ("Your X score is declining")

### 5. The Mirror Reveals Itself Over Time

Not a feature — a property of the system working correctly. Two small accelerants:
- **Birth animation:** Propositions visibly born after extraction. Flash at position, fade to rest.
- **Extraction feedback:** Momentary count ("3 new propositions") near phase space, fades in 2-3s.

---

## Demo Strategy

### Format: Deployed Web App + Local-First Product

**The demo is a web app.** URL a hiring manager can click, explore the 3D phase space, orbit, hover, switch modes. 60-120 seconds of direct interaction beats any video.

**The product is local-first.** Your data, your beliefs, your self-model — never lives on someone else's server. The distinction between deployed demo and local product demonstrates architectural sophistication: production deployment AND data sovereignty.

**Tech:** Dockerfile → Railway/Render. Pre-seeded `voku.db`. Demo mode (read-only or conversation-limited). ~4-6 hours total deployment work.

### Data: Synthetic Persona + Live Session Hybrid

**Pre-seeded:** 300-400 propositions from a synthetic persona with a designed 20-session arc. Relatable character (early-career professional navigating career direction, identity, relationships, health). NOT a famous person — the hiring manager should think "that could be me."

**Persona arc hits all 4 dimensions:**
- Pursuits: building a project, career pivot, questioning direction
- Self: identity evolution, confidence shifts, values crystallization
- Body: energy management, burnout signals, physical-mental connection
- Relationships: mentors, isolation, community seeking

**Designed belief evolution:** Clear turning points, contradictions that resolve, beliefs that strengthen or reverse. The phase space shows a visible developmental arc in time mode.

**Live session on top:** During demo, type a new message. Watch extraction happen. See propositions born into the populated space. The system works in real time on a foundation that already demonstrates the temporal thesis.

**Benefits:**
- No copyright issues (generated)
- No privacy exposure (fictional)
- Controlled arc (designed belief evolution)
- Natural language (modern, pipeline-friendly)
- Repeatable (deterministic demo state)
- The live overlay shows the system is real, not static

### Demo Narrative (60 seconds)

1. Open: populated phase space, 400 nodes, visible structure
2. Switch to dimension mode: four regions emerge, color field
3. Switch to time mode: developmental arc visible, early→recent
4. Hover nodes: see actual propositions, belief text
5. Live: type a message, watch extraction, new particles born
6. Close: "This is a temporal knowledge graph built from conversation. The system tracks how understanding evolves — beliefs forming, strengthening, contradicting, resolving."

---

## Technical Architecture for Demo

### Performance (validated by research)

- **InstancedMesh** for all nodes: 400-1000 nodes in 1 draw call
- **Shader-based animation** for breathing/floating: zero CPU cost
- **Bloom** with luminanceThreshold 0.9 + mipmapBlur: ~2-5ms on M1
- **Fog** always on: nearly free, adds depth, hides complexity
- **Text labels** distance-culled: only render within camera threshold
- Target: <10 draw calls total, 60fps on MacBook Air M1

### Stack (current, no changes needed)
- react-three-fiber v9.5 + Three.js r183 + drei
- Vite + React 19 + TS + Tailwind v4
- FastAPI + SQLite + bge-base-en-v1.5

### Migration path (post-demo)
- WebGPU renderer when r3f support stabilizes
- zustand for state management (extract from Workspace god component)
- InstancedMesh migration when node count exceeds 500

---

## Build Sequence (Updated)

### Phase A: Node Character (current session)
1. Size differentiation by dimensionRelevance (3 tiers)
2. Breathing animation (sine wave, phase offset per node)
3. Float animation (tiny y-drift)
4. Luminance pulse (emissive oscillation)
5. Soft halos on all nodes

### Phase B: Spatial Clarity
1. Remove cluster shells
2. Floating density labels (camera-gated)
3. Fix retrieval glow (server IDs primary, keywords secondary)
4. Dimension gravitational layout

### Phase C: Polish + Demo Prep
1. Birth animation (extraction → particles appear)
2. Extraction count notification
3. Dimension narrative labels (not numerical)
4. 2D companion view (timeline or card list)

### Phase D: Demo Deployment
1. Synthetic persona generation (20 sessions, 300-400 propositions)
2. Dockerfile + Railway deployment
3. Demo mode (read-only exploration + limited live chat)
4. Pre-seeded voku.db with curated arc

---

## Competitive Differentiators (for interviews/codewalk)

1. **Temporal knowledge graph from conversation** — no consumer product does this
2. **Visible, interactive user model** — ChatGPT builds a 6-layer profile but hides it; Voku makes it transparent
3. **3D phase space visualization** — no competitor uses particle physics / ecology metaphor
4. **Context engineering as core architecture** — not RAG, not fine-tuning, not prompt engineering
5. **Local-first product philosophy** — lessons from Dot/Limitless/Pi deaths inform architecture
6. **166 tests, ablation-ready evaluation** — production engineering, not tutorial project

---

## References

- Calm Technology (Amber Case, calmtech.com) — peripheral attention, pass-through interfaces
- Spotify Wrapped — identity narrative > numerical scores
- Claude Extended Thinking / Perplexity citations — "show your work" trust pattern
- Dot shutdown (Oct 2025) — cautionary tale for cloud-dependent companion AI
- Graphiti (Zep) — temporal KG infrastructure, validated architecture pattern
- ChatGPT memory reverse-engineering — hidden 6-layer profiling as design opportunity
- Knowledge graph practitioner study (arXiv 2304.01311) — hairball problem, domain-specific views
- Heptabase / Kosmik — 2D spatial canvas as current market leader in spatial knowledge
