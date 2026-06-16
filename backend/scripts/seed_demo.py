#!/usr/bin/env python3
"""
Seed Voku with a SYNTHETIC demo persona — safe to screenshot / deploy publicly.

Populates a knowledge graph for a fictional user ("Mina Park", a CS grad student
and indie builder) across six life domains. Each domain is a dense core of
recurring "daily log" lines (same structure, varying numbers/days) plus a few
unique reflections — which is exactly the redundancy that makes real accumulated
logs cluster. The real DBSCAN pass (eps=0.15 cosine, min_samples=3) then forms
one coloured cluster per domain; the reflections sit as connective noise.

Everything here is invented — no real personal data. Reuses the real ingestion
path (SQLiteTraceStorage + BGE embeddings + ConnectionService), so the resulting
graph is identical in kind to live usage. Fully offline: BGE runs locally, LLM
annotations are skipped (the phase space needs only traces + embeddings + edges).

Usage:
    cd backend && source venv/bin/activate
    python scripts/seed_demo.py                 # → ./data/demo.db (wipes + reseeds)
"""

import sys
import uuid
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.storage.sqlite_trace import SQLiteTraceStorage
from app.services.storage.models import Trace
from app.services.embedding.bge import BGEBaseEmbedding
from app.services.connections import ConnectionService


# ─── Per-domain generators ──────────────────────────────────────
# Each domain yields a dense log-core (templated near-paraphrases → clusters)
# plus a few unique reflections. `vals` cycles to vary the numbers/words.

def expand(templates, vals, n):
    """Produce n lines by cycling templates × value tuples."""
    out = []
    for i in range(n):
        tmpl = templates[i % len(templates)]
        v = vals[i % len(vals)]
        out.append(tmpl.format(*v))
    return out


DOMAINS = [
    {
        "title": "Lumen (the project)", "day": "2026-05-26", "hour": 20,
        "log_templates": [
            "Lumen dev log: built the {0} today. The FastAPI endpoint writes an append-only entry row to SQLite and the React form posts to it. {1} habits tracked now.",
            "Lumen build note: shipped {0}. Append-only entries, correction rows instead of edits, SQLite single file. The React frontend pulls aggregated entries from FastAPI. {1} habits so far.",
        ],
        "vals": [("entry-logging API", 3), ("the habit-streak view", 4), ("the mood slider", 5),
                 ("the rolling-average chart", 5), ("the sleep import", 6), ("correction rows", 6),
                 ("the energy score field", 7), ("the weekly summary", 7), ("the habit_log table", 8),
                 ("the entry edit-as-correction flow", 8)],
        "n_log": 16,
        "reflections": [
            "Lumen feels small and finished, which is exactly what I wanted from a single-user habit tracker — one SQLite file I can back up is the whole point.",
            "Designing Lumen append-only on purpose: never edit a mood entry in place, just write a correction row so the history stays honest over weeks.",
            "The Lumen read layer reconstructs current state by taking the latest row per logical entry. Clean split between the write model and the read model.",
        ],
    },
    {
        "title": "ML notes (transformers)", "day": "2026-05-28", "hour": 14,
        "log_templates": [
            "ML notes: re-derived {0} today. In the transformer it's about {1}. Query, key, value, attention — the same primitives keep showing up.",
            "Study log on {0}: the intuition is {1}. Worked it through with attention scores, softmax over tokens, and the value blend.",
        ],
        "vals": [("scaled dot-product attention", "each token asking who to listen to"),
                 ("multi-head attention", "several attention queries running in parallel"),
                 ("positional encoding", "injecting order because self-attention is a set operation"),
                 ("the query-key dot product", "a relevance score between two tokens"),
                 ("softmax over scores", "turning relevance scores into a distribution over tokens"),
                 ("embeddings as points", "meaning is nearness in a high-dimensional space"),
                 ("cosine similarity", "the angle between two embedding vectors"),
                 ("nearest-neighbour retrieval", "pulling the closest embeddings as context")],
        "n_log": 16,
        "reflections": [
            "Retrieval-augmented generation works because you store every chunk as an embedding, then pull the nearest neighbours as context — recall becomes geometry, reasoning stays with the model.",
            "Semantic-only retrieval makes an echo chamber: you get what's similar to what's similar. You need temporal and intentional edges over the embeddings to escape the topic.",
            "Self-attention is permutation-equivariant, so 'the dog bit the man' and 'the man bit the dog' embed alike until you add positional encoding.",
        ],
    },
    {
        "title": "Marathon training", "day": "2026-05-30", "hour": 9,
        "log_templates": [
            "Training log: easy Zone 2 run today, {0}k at conversational pace, heart rate held under {1} bpm. Weekly mileage {2}k, marathon base building.",
            "Run log: {0}k easy aerobic, Zone 2, heart rate under {1}. Felt almost too slow. Weekly running mileage now {2}k. Base block, 80/20 easy.",
        ],
        "vals": [(8,142,38),(10,145,40),(7,140,36),(9,144,41),(11,146,43),(6,138,35),
                 (12,148,44),(8,141,39),(10,143,42),(9,145,40),(13,150,45),(7,139,37)],
        "n_log": 16,
        "reflections": [
            "Eight weeks to the half marathon. The 80/20 rule: most running volume easy in Zone 2, a small dose hard. Running easy days hard is why I keep getting injured.",
            "Cardiac drift at fixed easy effort is normal in heat — heart rate creeps up to hold pace as plasma volume drops. A shrinking drift over weeks is fitness.",
            "Taper week: cut weekly mileage 40%, fitness is already banked, just shedding fatigue. Resting heart rate ticked down 3 bpm — absorbing the training load.",
        ],
    },
    {
        "title": "Index investing", "day": "2026-06-01", "hour": 19,
        "log_templates": [
            "Investing note: index-fund portfolio set to {0}% global equity ETF, {1}% bond ETF, rebalance {2}. Boring, rules-based, no tinkering.",
            "Portfolio log: {0}/{1} split across a global equity ETF and a bond ETF, calendar rebalance {2}. Designing out my urge to trade.",
        ],
        "vals": [(80,20,"every June and December"),(75,25,"twice a year"),(85,15,"semi-annually"),
                 (80,20,"on a fixed calendar"),(70,30,"every six months"),(78,22,"in June and December"),
                 (82,18,"twice annually"),(76,24,"on schedule")],
        "n_log": 14,
        "reflections": [
            "Rebalancing the portfolio means selling the ETF that went up and buying the one that went down to restore target weights. It feels wrong every time, which is why it works.",
            "Costs and behaviour dominate long-run portfolio returns far more than security selection. A rules-based rebalance removes the discretionary trade where losses happen.",
            "The whole investing system is now three lines of rules I won't override — allocation, rebalance cadence, and never touch it otherwise.",
        ],
    },
    {
        "title": "Reading & focus", "day": "2026-06-03", "hour": 22,
        "log_templates": [
            "Reading note on Deep Work: {0}. Focus as a trainable capacity, not a fixed trait.",
            "Deep Work note: {0}. Distraction is a habit you can reshape, not a character flaw.",
        ],
        "vals": [("the ability to focus without distraction is rare and valuable at once",),
                 ("scarcity plus value is where leverage lives, and deep focus is both",),
                 ("shallow work expands to fill the time you give it",),
                 ("schedule deep-focus blocks first and let shallow work fight for the rest",),
                 ("my deep work collapses when I context-switch between projects in one block",),
                 ("batching focus by domain protects the depth better than batching by time",),
                 ("attention residue from task-switching is the hidden tax on shallow days",),
                 ("a daily shutdown ritual is what lets the deep blocks stay deep",)],
        "n_log": 13,
        "reflections": [
            "The strongest claim in Deep Work is that focus is trainable — that reframes distraction from a personality flaw into a habit I can reshape with structure.",
            "I notice my own deep work collapses when I jump between Lumen, study, and training planning in the same block — batching by domain might protect it.",
        ],
    },
    {
        "title": "Co-op / career prep", "day": "2026-06-05", "hour": 11,
        "log_templates": [
            "Co-op prep: rehearsing the {0} in {1} so I can whiteboard it cold for interviews. A project I can't defend is a liability, not an asset.",
            "Interview prep log: drilled {0} for {1} — derive it on the whiteboard, then name what it does NOT do. That last part reads as senior.",
        ],
        "vals": [("embedding-and-graph retrieval", "the notes-to-graph tool"),
                 ("append-only data model", "Lumen"),
                 ("DBSCAN clustering step", "the notes-to-graph tool"),
                 ("rolling-average aggregation", "Lumen"),
                 ("nearest-neighbour search", "the notes-to-graph tool"),
                 ("FastAPI + SQLite architecture", "Lumen"),
                 ("graph expansion over embeddings", "the notes-to-graph tool"),
                 ("correction-row supersede logic", "Lumen")],
        "n_log": 14,
        "reflections": [
            "My two portfolio projects are complementary, not redundant: Lumen is shipped full-stack product engineering, the notes-to-graph tool is applied ML and retrieval. That's range.",
            "The real co-op risk is a project I can't defend — if an interviewer asks how my retrieval works and I hand-wave, that's worse than not having built it.",
            "Co-op prep plan: pick the one hard mechanism per portfolio project, rehearse until I can derive it, and practice naming each project's limitations.",
        ],
    },
]


def build_traces() -> list[Trace]:
    traces: list[Trace] = []
    for d in DOMAINS:
        conversation_id = str(uuid.uuid4())
        base = datetime.strptime(d["day"], "%Y-%m-%d").replace(hour=d["hour"], tzinfo=timezone.utc)
        lines = expand(d["log_templates"], d["vals"], d["n_log"]) + d["reflections"]
        parent_id = None
        for offset, content in enumerate(lines):
            # logs are 'user' captures; the trailing reflections alternate for visual variety
            source = "assistant" if (offset >= d["n_log"] and offset % 2 == 0) else "user"
            trace = Trace(
                id=str(uuid.uuid4()),
                timestamp=(base + timedelta(minutes=3 * offset)).isoformat(),
                content=content,
                conversation_id=conversation_id,
                parent_trace_id=parent_id,
                source=source,
            )
            traces.append(trace)
            parent_id = trace.id
    return traces


def seed(db_path: str) -> None:
    import sqlite3

    traces = build_traces()
    print(f"Synthetic persona → {len(traces)} traces across {len(DOMAINS)} domains")

    storage = SQLiteTraceStorage(db_path)
    conn = sqlite3.connect(db_path)
    for table in ["traces", "embeddings", "annotations", "connections", "resources"]:
        try:
            conn.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

    print("Loading BGE embedding model (first run downloads ~420MB)...")
    embedder = BGEBaseEmbedding()

    for trace in traces:
        storage.store_trace(trace)
    print(f"  ✓ {len(traces)} traces stored")

    contents = [t.content for t in traces]
    embeddings = embedder.embed_batch(contents)
    for trace, emb in zip(traces, embeddings):
        storage.store_embedding(trace.id, emb, embedder.model_name)
    print(f"  ✓ {len(traces)} embeddings stored")

    counts = ConnectionService(storage).compute_all(k=5, threshold=0.3)
    print(f"  ✓ connections — temporal: {counts['temporal']}, semantic: {counts['semantic']}")

    storage.close()
    print(f"\nSEED COMPLETE → {db_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Voku with a synthetic demo persona")
    parser.add_argument("--db-path", default="./data/demo.db", help="Target DB (default: ./data/demo.db)")
    args = parser.parse_args()
    seed(args.db_path)
