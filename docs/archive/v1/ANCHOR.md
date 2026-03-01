# Voku — Anchor Document

**Created:** 2026-02-18
**Updated:** 2026-02-25 (Product/framework separation — philosophy moved to vault)
**Author:** Jaymin Chang
**Status:** This is the product definition. What we're building and how.

---

## What It Is

A personal cognitive environment. The user thinks out loud through conversation. The system accumulates understanding across sessions, assembles context intelligently for each interaction, and visualizes the evolving knowledge structure in real time through an interactive 3D phase space alongside the chat.

## The Core Technical Bet

You don't personalize the model. You make the context assembly so intelligent that a general model behaves as if it were personalized. The intelligence is in what gets assembled — which memories, summaries, and extracted insights, at what compression level — not in the model weights.

## Demo Target (March 31)

Day 3 is meaningfully better than Day 1. The user sees the same underlying data reshape depending on what they're currently thinking about. Contextual resolution is visible — not just better responses, but the user watching context assemble in real time.

## Three Design Principles

### 1. Conversation Is Cognition
The user thinks out loud. Extraction happens invisibly. The knowledge structure builds as a side effect of a behavior the person already wants to perform.

### 2. Emergent Structure
Data points arrive with geometric properties that place them in a space. Structure self-organizes — clusters form, chains emerge, attractors stabilize. The system navigates the topology data creates, not predefined categories.

### 3. Broad Storage, Narrow Retrieval
Storage asks almost nothing — when, what conversation, reasonable name. Retrieval asks everything — given this specific context, what's relevant? Scope comes from the task at retrieval time, not from classification at ingestion.

## Visualization: Phase Space

Points positioned by their geometric properties. Proximity is the primary relationship. Same data, different projection = different view. New data naturally reshapes the landscape without maintenance.

**Tech:** Three.js via react-three-fiber. Validated in Spike A (Feb 18).

## Current State

Full vertical slice working: chat → extraction → assignment → score → context assembly → chat. 181 tests passing. Phase space with InstancedMesh rendering, k-NN edges, cluster shells, multiple layout modes. Frontend: ChatPanel decomposition, design tokens, dark/light split.

**Codebase:** ~48 Python files (~4,200 LOC), 25 TS files (~3,400 LOC).
**Database:** Single SQLite. 425 propositions, 425 embeddings, 15 conversations, 4 user_model dimensions.
**Git:** Branch `feat/phase-b-chat-edges` at `80b5327`. Main at `9c6bf6d` (49 commits).

## Build Plan (Demo-Priority)

**Phase B3:** Edge layers + co-cognition foundation (selective bloom, retrieval activation via SSE, edge pulse shader, keyword glow, legend overlay)

**Phase C1 (demo-critical):** Birth animation, extraction summary, message block highlighting, onboarding hints, context label

**Phase D:** Synthetic persona, Dockerfile + Railway, demo mode, pre-seeded voku.db

**Minimum viable demo: through C1.** Remaining: ~6 sessions → before Mar 31.

## Architecture Note

This version of Voku stores extracted propositions as discrete strings with confidence scores. This is a known representational limitation — the framework work in the vault explores alternative architectures (contextual potentials, sheaf-structured storage) that would replace proposition-level storage. The current demo proves the context engineering thesis. Future versions may rebuild from a different representational foundation entirely.

---

## Philosophical Framework

The deeper "why" — design philosophy, theoretical foundations, cross-disciplinary synthesis — lives in the vault, not this repo. See:
- `brain/concepts/contextual cognitive potentials — framework.md`
- `brain/concepts/voku — north star vision.md`
- `brain/sessions/2026-02-25_framework-emergence.md`

The framework is the intellectual contribution. This product is one expression of it.
