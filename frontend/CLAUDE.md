# Voku Frontend — Claude Code Instructions

## Stack
React 19, TypeScript, Vite, Tailwind v4, Three.js via react-three-fiber (@react-three/fiber), @react-three/drei

## Dev server
`npm run dev` → localhost:5173
Backend must be running on localhost:8000 for chat/phase space data.

## Phase space components (the 3D visualization)
- `src/components/phase-space/TraceCloud.tsx` — InstancedMesh nodes (octahedron geometry, vertex colors)
- `src/components/phase-space/EdgeMesh.tsx` — k-NN edges as bezier curves (LineSegments)
- `src/components/phase-space/ClusterCloud.tsx` — translucent cluster shells
- `src/components/phase-space/PhaseSpaceScene.tsx` — Canvas, lighting, composition
- `src/components/phase-space/CameraController.tsx` — OrbitControls + auto-framing

## Design tokens
All colors/spacing live in `src/styles/tokens.css`. Light mode (warm cream base).

## Iteration workflow
1. Make ONE focused change at a time
2. Use Playwright to screenshot localhost:5173 after each change
3. Assess the screenshot before making the next change
4. The phase space is at the right half of the screen — open it with Cmd+Space in the UI, or it auto-opens
5. Target aesthetic: clean, readable, information-dense. NOT dark mode. Warm cream background.

## Current known issues
- Nodes may be too large or too dark — adjust baseSize and colors in TraceCloud.tsx
- Cluster shells need to be visible but not overwhelming
- Edges should be subtle gray arcs, gold when retrieval is active

## Key constraint
TypeScript must compile clean (`npx tsc --noEmit`) before considering any change done.
