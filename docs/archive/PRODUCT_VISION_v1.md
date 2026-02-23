# Voku Product Vision

> One page. This is the product, not the architecture.

**Last Updated:** 2026-02-17

---

## What It Is

An interactive journaling app where people think out loud and the system gets smarter about them over time. The user talks — processes their day, brainstorms ideas, works through decisions, vents, reflects. The system listens with continuity across sessions, accumulates structured self-knowledge, and surfaces it in future conversations.

## Why People Use It

People already talk to AI. They open Claude or ChatGPT and start processing their lives — career decisions, relationship dynamics, health patterns, creative projects. They surprise themselves with what comes out. Then the session ends and the insight evaporates.

This app is what happens when that flow state has a persistent, accumulating memory behind it. Session 5 you're not starting over. You're going deeper because the system holds what you already surfaced.

The therapeutic comparison is exact. Therapy works not because of the therapist's advice but because someone listens with continuity across sessions, and that continuity makes the speaker go deeper than they would alone. This app provides that continuity without the $150/hour price tag and without sharing your data with anyone.

## The Virtuous Loop

The UI must make people *want* to externalize. If it feels like a productivity tool, people use it like a task. If it feels like a space to think — warm, responsive, maybe playful — people open up. The more they open up, the better the extraction. The richer the accumulated context, the more valuable the next session. The more valuable the next session, the more they open up.

**UI quality → user openness → data quality → context quality → session value → user return.**

The design question the UI must answer: "What makes someone want to come back and talk more?"

## What the User Sees

**Day 1:** A warm chat interface. They start talking. The responses are good — frontier model quality. It feels like Claude or ChatGPT but with a different vibe. More listening, less performing. At the end, nothing special happens. They close it.

**Day 3:** They open the app. The system references something from day 1 they'd forgotten they said. Not in a creepy way — in the way a good friend remembers what you were worried about last week. The conversation goes somewhere it couldn't have gone on day 1 because the context exists.

**Day 30:** The system knows their patterns. "You've mentioned afternoon energy crashes in 8 of your last 20 sessions, mostly on days you skipped your morning routine." The user didn't ask for this. The system surfaced it because the accumulated context made it visible. The user sees something about themselves they couldn't see alone.

## What the System Does

1. **Stores every conversation immutably.** Nothing is lost, nothing is modified. The user's words are the source of truth.
2. **Compresses older conversations into summaries.** Hierarchical DAG (from LCM paper). Lossless — originals always recoverable. The user never hits a context limit.
3. **Extracts structured insights.** After each conversation, the system identifies claims, decisions, patterns, intentions. These become searchable, retrievable knowledge about the user.
4. **Assembles personalized context.** Each new conversation gets a curated context window: recent messages + relevant summaries + extracted insights. The model sees what matters, not everything.
5. **Gets better over time.** More conversations → richer extractions → better context assembly → more useful responses. The product improves through use, not through updates.

## What It Is Not

- Not a task manager or productivity tool
- Not an AI advisor that tells you what to do
- Not a therapist replacement (no clinical claims)
- Not a social platform
- It IS a mirror. The product of using it is seeing yourself more clearly.

## Technical Foundation

- **Context management:** LCM paper (Ehrlich & Blackman, 2026) — immutable store + hierarchical summary DAG
- **Knowledge structuring:** Ars Contexta — callable claims, test-driven knowledge checks
- **Extraction:** Existing Voku pipeline (constraints-led, 94.7% classification accuracy)
- **Inference:** Provider-agnostic. Anthropic API (Sonnet 4.5) now, local models when quality catches up
- **Storage:** Local-first. SQLite. User owns their data.
- **Cost:** $3-10/month API cost per user. Viable at $10-15/month subscription.

## North Star

Build tools that help humans see themselves. The intervention is the artifact, not the explanation. The six-year-old builder makes something → someone interacts with it → they see something they couldn't see before → that seeing changes what they do next.
