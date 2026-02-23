# Voku — Anchor Document

**Created:** 2026-02-18
**Updated:** 2026-02-18 (Spike A session — phase space validated)
**Author:** Jaymin Chang
**Status:** This is the north star. Everything builds from this.

---

## What It Is

A personal digital environment that keeps user-centric and task-centric data. The user thinks out loud through conversation. The system accumulates understanding across sessions, assembles context intelligently for each interaction, and visualizes the user's evolving knowledge structure in real time through an interactive 3D phase space alongside the chat.

Data points arrive with geometric properties — embedding coordinates, temporal position, conversational context — that place them in a space. As more points arrive, structure self-organizes. The visualization is a live view of the system's context window: each message updates what the system thinks is relevant, and the graph reflects that in real time.

## Why It Exists

It gives individuals the playground to properly integrate AI into their lives in a healthy way while still holding the power of decision making. Voku provides vision and suggestions based on what the user has shared with it — nothing more. No ads, no hidden optimization, no misaligned incentives.

## What Makes It Different

**Trustworthy** — the user can see the evidence behind Voku's understanding. The organization is unbiased and acting in the user's interest.

**Consistent** — the system doesn't contradict itself across sessions.

**Persistent** — nothing is lost. Conversations are immutable. Compression is hierarchical, not destructive.

**Objective** — Voku surfaces what the user actually said and did, not what they wish they said.

## The Core Technical Bet

You don't personalize the model. You make the context assembly so intelligent that a general model behaves as if it were personalized. The intelligence is in what gets assembled — which memories, summaries, and extracted insights, at what compression level — not in the model weights. Dynamic context responsive to the user's current intent, not static feature additions. Changing weights, not adding layers.

## Three Design Principles

### 1. Conversation Is Cognition

Self-discovery, goal clarity, belief evolution are not features to engineer. They are emergences — proof the substrate is working. Voku builds the substrate: persistent conversation, intelligent context assembly, visual knowledge structure. Building the emergences directly would be adding layers. Building the substrate is changing weights.

### 2. Emergent Structure

Data points arrive with geometric properties that place them in a space. As more points arrive, structure self-organizes — clusters form, chains emerge, attractors stabilize. The system doesn't interpret data points — it navigates the topology they create. A single data point has no fixed valence; its meaning depends on which goals exert gravitational pull and what else is nearby. Same data, different projection, different structure.

This replaces "deferred interpretation." The ingestion constraint remains (don't over-classify at storage time — see CONSTRAINTS.md), but the system behavior is active, not passive. Structure is always forming, not waiting to be activated.

### 3. Broad Storage, Narrow Retrieval

Storage asks almost nothing — when, what conversation, reasonable name. Everything gets kept. Retrieval asks everything — given this specific task, this specific user context, what stored data is relevant? The scope comes from the task at retrieval time, not from classification at ingestion. Same data, different retrieval, different result every time depending on what the user is doing.

## Visualization Model: Phase Space

The graph is not a knowledge map with curated edges. It is a phase space — points positioned by their geometric properties, with proximity as the primary relationship. No edges to curate. Structure emerges from the distribution of points.

**Why phase space over knowledge graph:**
- No edge curation needed. Proximity *is* the relationship.
- Same data, different projection = different view. Selecting a goal reshapes the topology.
- New data naturally reshapes the landscape without maintenance.
- Goals and themes emerge as attractors, not predefined categories.
- Trajectories are visible — thinking evolution traced as paths through space.
- Connects to motor learning foundation: constraints-based self-organization.

**What the graph shows:**
- The live state of the system's context window
- Each message updates which nodes are relevant — active nodes brighten, irrelevant nodes recede
- Cross-domain connections light up when bridging concepts activate together
- The user watches context assemble in real time — "the system is thinking with me"

**Over time:**
- Co-activation patterns stabilize into emergent modules (clusters that reliably activate together = a "domain")
- The system learns query patterns — "when this user's opening message looks like X, the useful context is Y and Z"
- Goals are not predefined — they emerge as stable attractor patterns across conversations

**Tech:** Three.js via react-three-fiber. Validated in Spike A (Feb 18).

## Data Sources

Conversation is the primary and richest input — intentional, reasoned, interpretive. But not the only source. Behavioral data (calendar, tasks, files), tracked metrics (health, spending, training), and consumed content (articles, papers) progressively feed in. Conversation is the interpretation layer — raw data becomes meaningful when the user explains what it means to them. More data makes conversation smarter, better conversation produces richer context, richer context draws the user back.

## User Experience

**Day 1.** A chat interface alongside a 3D phase space that populates as the user talks. Points appear, positioned by their content. As the conversation develops, some points brighten, others recede. Cross-domain connections flash when bridging ideas surface. The user watches their thinking take shape in space.

**Day 10.** The space has structure — visible clusters, temporal chains, regions of density. Typing a message activates the relevant constellation. The user feels known without having been quizzed. The system's context assembly is noticeably better than day 1.

**Day 30.** Emergent modules have stabilized. The opening message acts as a projection that reshapes the space around the user's intent. The system has learned which constellations co-activate. Multiple data sources feeding in. The workspace reflects the user's life — not as a static map, but as a living landscape that responds to what they're thinking about right now.

## Interaction Model

The chat is the input modality. The phase space is interactive — the user can orbit, zoom, select nodes, click goal attractors to reshape the projection. AI provides expert suggestions; the user defines the scope and makes decisions. The system learns workflows by observing co-activation patterns across conversations.

## What Voku Is Not

It does not directly build the things that emerge from the fundamentals. Self-discovery, goal tracking, belief evolution — these are proof the system works, not features to be engineered. Voku builds the substrate. The emergences take care of themselves.
