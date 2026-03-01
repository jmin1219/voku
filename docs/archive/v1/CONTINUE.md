# Voku Session Continuation

> Copy-paste this to start next session.

## Prompt

Continue Voku development. Session type: **Phase B3: Edge Layers + Co-Cognition Foundation**

Read `docs/STATE.md` and `docs/INTERACTION_DESIGN.md` for full context.
For design philosophy: `docs/VISION.md` (439 lines — the *why*).
For visual vocabulary: `docs/INTERACTION_DESIGN.md` (261 lines — the *feel*).

**COMPLETED:**
- ~~Builds 1-4~~ ✅ (vertical slice complete, 181 tests)
- ~~Phase A: Node Character~~ ✅ (size hierarchy, breathing, camera, dark/light)
- ~~Phase B1: ChatPanel decomposition~~ ✅ (design tokens, textarea, timestamps, critical fixes)
- ~~Phase B2: InstancedMesh + k-NN edges~~ ✅ (NodeCloud, EdgeMesh, 1582 edges, 429 nodes in 1 draw call)

**DOC STACK:** ANCHOR.md (what) → VISION.md (why) → THEORY.md (ideas) → DESIGN_STRATEGY.md (how) → INTERACTION_DESIGN.md (feel) → CONSTRAINTS.md (rules)

**VERTICAL SLICE COMPLETE:** chat → extract → assign → exhale → context assembly → chat.

**NEXT: Phase B3 — Edge Layers + Co-Cognition Foundation**

Five items, priority order:

1. **Selective bloom** — UnrealBloomPass + THREE.Layers. Active/important nodes glow. Params: strength 0.5, radius 0.6, threshold 0.15. ~50 LOC. Single biggest visual upgrade.

2. **Retrieval activation via SSE event** — Backend emits `event: retrieval` with `{nodeIds: [...]}` BEFORE response stream. Frontend catches this, triggers node activation cascade (staggered emissive increase, edge pulse on connecting edges). THE core co-cognition moment. ~15 LOC backend, ~30 LOC frontend.

3. **Edge pulse shader** — Add `uniform float uTime` to EdgeMesh's ShaderMaterial. Fragment: `float pulse = smoothstep(0.0, 0.3, sin(vProgress * 6.28 - uTime * 2.0))`. Active edges flow with energy during retrieval. ~10 LOC.

4. **Keyword glow (mid-message)** — `useEffect` with 500ms debounce on textarea value. Scan against node labels (case-insensitive). Update `Set<nodeId>` read by `useFrame` to adjust emissive. ~20 LOC. Space feels alive during typing.

5. **Legend overlay + density labels** — PhaseSpaceOverlay component with mode switcher and dimension key. Floating labels near cluster density centers (low opacity, camera-distance gated).

**See INTERACTION_DESIGN.md "Seven Moments of Conversation"** for the full interaction lifecycle these items implement.

**CURRENT RENDERING PIPELINE:**
- NodeCloud.tsx: InstancedMesh, custom ShaderMaterial, per-instance attributes
- EdgeMesh.tsx: THREE.LineSegments, weight→intensity, retrieval dimming ×0.5
- ClusterShell.tsx: Translucent sphere wireframes around DBSCAN clusters

**DATABASE STATE:**
- `data/voku.db`: 429 propositions, 425 embeddings, 1582 edges (k=5 k-NN), 15 conversations, 31 messages
- 4 user_model dimensions (all populated), 508 model_evidence assignments

**GIT:** Branch `feat/phase-b-chat-edges` at `80b5327`. 9 ahead of main. Clean.

**TESTS:** 181 passing

**KEY DESIGN DECISIONS (Session 16):**
- Retrieval results must be separate SSE event BEFORE response stream
- No confirmation gate on extraction — visible birth, not gated
- Every visual change reflects real computation — no cosmetic animation
- Chat is write interface, phase space is read interface — no manual node creation

**STARTUP:**
- Backend: `cd backend && . venv/bin/activate && python -m uvicorn app.main:app --reload`
- Frontend: `cd frontend && NODE_ENV=development npm run dev`