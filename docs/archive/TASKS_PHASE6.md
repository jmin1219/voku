# Phase 6: Frontend — Multi-Resolution Phase Space — Task Breakdown

**Created:** 2026-03-01
**SPEC ref:** § Build Sequence Phase 6
**Test strategy:** Visual verification (no automated frontend tests in current stack)

---

## Group A: Container + Data Layer

### Task 6.1: Phase space data hook

**What:** `usePhaseSpace()` hook fetches `/api/phase-space`, returns typed data (nodes, clusters, orientations, edges), exposes loading/error state. Re-fetches on demand (not polling).

**Changes:**
- New: `src/hooks/usePhaseSpace.ts`
- New: `src/types/phase-space.ts` — TypeScript interfaces matching backend response

**Acceptance criteria:**
1. Hook returns `{ nodes, clusters, orientations, edges, meta, loading, error, refetch }`
2. Types match backend response shape (node has cluster, orientation, position, annotations)
3. Doesn't fetch until explicitly called (lazy — phase space starts hidden)

---

### Task 6.2: Summonable container

**What:** Phase space slides in from right on ⌘+Space (Mac) / Ctrl+Space (Win). Dismissed with same shortcut or Escape. Remembers open/closed state. Chat remains accessible beneath (width compression).

**Changes:**
- New: `src/components/phase-space/PhaseSpaceContainer.tsx` — overlay container with slide animation
- Modified: `src/pages/Workspace.tsx` — keyboard listener, state management, layout adjustment

**Acceptance criteria:**
1. ⌘+Space toggles phase space open/closed
2. Escape closes when open
3. Chat compresses to ~50% width when phase space is open
4. Smooth slide-in animation (CSS transition, ~200ms)
5. Phase space fetches data on first open (not on page load)
6. Container has dark background (--voku-phase-bg)

---

## Group B: Trace-Level Rendering

### Task 6.3: Trace scatter with InstancedMesh

**What:** Render nodes as instanced spheres at UMAP positions. Shape encodes source type (sphere=user, box=assistant). Color encodes recency (warm gold → cool slate). Size from connectivity.

**Changes:**
- New: `src/components/phase-space/TraceCloud.tsx` — InstancedMesh renderer
- New: `src/components/phase-space/PhaseSpaceScene.tsx` — R3F Canvas + camera + lights

**Acceptance criteria:**
1. All nodes render at correct UMAP positions from API
2. User traces are spheres, assistant traces are boxes
3. Color gradient: recent = gold/amber, old = slate/blue-grey
4. Hover shows trace label (first 80 chars)
5. 60fps at 500 nodes (InstancedMesh, not individual meshes)

---

### Task 6.4: Retrieval glow

**What:** When chat has active retrieval IDs, corresponding nodes in phase space glow gold. Glow fades after 3 seconds.

**Changes:**
- Modified: `src/pages/Workspace.tsx` — pass retrievalIds to phase space
- Modified: `TraceCloud.tsx` — per-instance emissive intensity driven by retrieval state

**Acceptance criteria:**
1. Nodes matching retrievalIds glow brighter (emissive gold)
2. Glow activates when new retrieval IDs arrive from chat
3. Glow fades over ~3s (not instant off)
4. Non-retrieved nodes remain at base brightness

---

### Task 6.5: k-NN edge mesh

**What:** Render k-NN edges as thin lines between connected nodes. Subtle at rest, slightly brighter for edges connecting retrieved nodes.

**Changes:**
- New: `src/components/phase-space/EdgeMesh.tsx` — LineSegments with BufferGeometry

**Acceptance criteria:**
1. Edges render between connected node pairs
2. Edge opacity ~0.15 at rest (subtle ambient web)
3. Edges connecting retrieved nodes brighten to ~0.4
4. No self-edges rendered

---

## Group C: Cluster Clouds + Interaction

### Task 6.6: Cluster cloud shells

**What:** At mid-zoom, render soft translucent shells around cluster boundaries. Labels appear on hover/click.

**Changes:**
- New: `src/components/phase-space/ClusterCloud.tsx` — translucent sphere at cluster center

**Acceptance criteria:**
1. Each cluster renders as a soft translucent sphere at cluster center
2. Sphere radius matches cluster radius from API
3. Hover shows cluster label + "~N traces about..."
4. Clusters colored by recency (average of member traces)

---

### Task 6.7: EchoMind focus + camera

**What:** Click a node or cluster → camera orbits to focus on it, neighborhood expands, rest compresses to ambient. OrbitControls for manual navigation. Scroll to zoom.

**Changes:**
- New: `src/components/phase-space/CameraController.tsx` — OrbitControls + focus animation
- Modified: `TraceCloud.tsx` — focus state dims non-focused nodes

**Acceptance criteria:**
1. Click node → camera smoothly orbits to center on it
2. Focused node and its k-NN neighbors remain bright
3. Non-focused nodes dim to ~30% opacity
4. Click empty space → reset to default view
5. Scroll zooms in/out
6. Mouse drag orbits

---

## Deferred

- Orientation-level rendering (terrain) — Phase 7
- Continuous zoom interpolation between levels — Phase 7
- Time slider — Phase 7
- Thread paths on selection — Phase 7
- Contradiction edges (dashed) — Phase 7

---

## Gates

| Group | Gate |
|-------|------|
| A | ⌘+Space opens/closes phase space. Data loads on first open. Types compile. |
| B | Nodes render at positions. Retrieval glow works from chat. Edges visible. 60fps. |
| C | Cluster shells visible. Click-to-focus works. Camera orbit smooth. |
