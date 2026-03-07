#!/usr/bin/env python3
"""
Seed Voku database from vault session logs.

Reads markdown session logs, parses them into traces, embeds them,
and populates the Voku SQLite database with realistic multi-domain data.

Usage:
    cd /path/to/voku/backend
    source venv/bin/activate
    python scripts/seed_from_sessions.py --sessions-dir /path/to/session/logs

Options:
    --sessions-dir   Path to vault session logs directory
    --db-path        Path to voku.db (default: ./data/voku.db)
    --max-files      Max number of session files to process (default: all)
    --dry-run        Parse and print stats without writing to DB
    --skip-annotations  Skip LLM annotation extraction (faster, no API needed)
"""

import sys
import os
import re
import uuid
import argparse
import glob
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.storage.sqlite_trace import SQLiteTraceStorage
from app.services.storage.models import Trace, Connection
from app.services.embedding.bge import BGEBaseEmbedding
from app.services.connections import ConnectionService


# ─── Domain classification heuristics ───────────────────────────

DOMAIN_KEYWORDS = {
    "career": ["career", "co-op", "resume", "portfolio", "north star", "job", "interview", "networking", "linkedin"],
    "academics": ["cs5004", "cs5008", "cs5800", "assignment", "lab", "midterm", "quiz", "java", "oop", "dsa", "sorting", "homework", "lecture"],
    "voku": ["voku", "billy", "trace", "proposition", "embedding", "knowledge graph", "phase space", "annotation", "retrieval"],
    "training": ["training", "rowing", "2k", "bike", "cardio", "harris", "jamieson", "strength", "orthostatic", "breathing", "nutrition", "hrv"],
    "finance": ["finance", "portfolio", "etf", "questrade", "tfsa", "fhsa", "investment", "stock", "spending"],
    "emotional": ["fear", "loneliness", "monitor", "vulnerability", "시리다", "aching", "shadow", "emotional", "identity", "motherly"],
    "technical": ["architecture", "docker", "fastapi", "react", "typescript", "python", "api", "database", "mcp", "llm"],
    "brain-dump": ["brain dump", "externalize", "scope", "framework", "throughline", "consciousness", "cognition"],
}


def classify_domain(text: str) -> str:
    """Classify text into a domain based on keyword frequency."""
    text_lower = text.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


# ─── Source type heuristics ─────────────────────────────────────

USER_SECTION_PATTERNS = [
    r"raw capture", r"what happened", r"context", r"brain.?dump",
    r"the pattern", r"the fear", r"journal", r"morning", r"evening",
    r"items logged", r"current state",
]
ASSISTANT_SECTION_PATTERNS = [
    r"key findings", r"key decisions", r"synthesis", r"analysis",
    r"what.?s next", r"next steps", r"action items", r"recommendation",
    r"intervention", r"assessment", r"takeaway",
]


def classify_source(section_header: str, content: str) -> str:
    """Determine if a section is user thinking or assistant analysis."""
    header_lower = section_header.lower()
    for pat in ASSISTANT_SECTION_PATTERNS:
        if re.search(pat, header_lower):
            return "assistant"
    for pat in USER_SECTION_PATTERNS:
        if re.search(pat, header_lower):
            return "user"
    # Default: user (session logs are primarily Jaymin's thinking)
    return "user"


# ─── Markdown parsing ───────────────────────────────────────────

def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter if present."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].strip()
    return text


def parse_session_file(filepath: str) -> dict:
    """Parse a session markdown file into structured sections.

    Returns:
        {
            "filename": str,
            "date": datetime,
            "title": str,
            "sections": [{"header": str, "content": str, "source": str}]
        }
    """
    path = Path(filepath)
    filename = path.stem  # e.g., "2026-01-21_central-fear"

    # Extract date from filename
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
    if date_match:
        date = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        # No date in filename (e.g., reference files) — use file modification time
        mtime = os.path.getmtime(filepath)
        date = datetime.fromtimestamp(mtime, tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    text = strip_frontmatter(raw)
    if not text.strip():
        return None

    # Extract title from first # header
    title_match = re.match(r"#\s+(.+)", text)
    title = title_match.group(1).strip() if title_match else filename

    # Split by ## headers
    sections = []
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract header
        header_match = re.match(r"##\s+(.+)", part)
        if header_match:
            header = header_match.group(1).strip()
            content = part[header_match.end():].strip()
        else:
            # Content before first ## (intro / title area)
            header = "overview"
            # Skip the # title line itself
            lines = part.split("\n")
            content_lines = [l for l in lines if not l.startswith("# ")]
            content = "\n".join(content_lines).strip()

        if len(content) < 30:
            continue  # Skip trivially short sections

        source = classify_source(header, content)
        sections.append({
            "header": header,
            "content": content,
            "source": source,
        })

    return {
        "filename": filename,
        "date": date,
        "title": title,
        "sections": sections,
    }


# ─── Chunking: split long sections into paragraph-sized traces ──

MAX_TRACE_CHARS = 1500  # ~300 words max per trace
MIN_TRACE_CHARS = 50


def chunk_content(content: str) -> list[str]:
    """Split long content into paragraph-sized chunks.

    Splits at double newlines (paragraphs), then at single newlines
    if paragraphs are still too long. Merges very short chunks.
    """
    # Split at paragraph breaks
    paragraphs = re.split(r"\n\n+", content)
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If adding this paragraph keeps us under limit, merge
        if current and len(current) + len(para) + 2 <= MAX_TRACE_CHARS:
            current += "\n\n" + para
        else:
            if current and len(current) >= MIN_TRACE_CHARS:
                chunks.append(current)
            current = para

    if current and len(current) >= MIN_TRACE_CHARS:
        chunks.append(current)

    # If we ended up with nothing (content was one big block), split by lines
    if not chunks and len(content) > MAX_TRACE_CHARS:
        lines = content.split("\n")
        current = ""
        for line in lines:
            if current and len(current) + len(line) + 1 > MAX_TRACE_CHARS:
                if len(current) >= MIN_TRACE_CHARS:
                    chunks.append(current)
                current = line
            else:
                current = (current + "\n" + line) if current else line
        if current and len(current) >= MIN_TRACE_CHARS:
            chunks.append(current)

    # If still nothing, just use the whole content
    if not chunks and len(content) >= MIN_TRACE_CHARS:
        chunks.append(content[:MAX_TRACE_CHARS])

    return chunks


# ─── Time assignment ────────────────────────────────────────────

# Assign realistic session times based on filename cues
TIME_CUES = {
    "morning": (9, 0),
    "afternoon": (14, 0),
    "evening": (19, 0),
    "winddown": (21, 0),
    "night": (22, 0),
}


def assign_base_time(filename: str, date: datetime) -> datetime:
    """Assign a realistic time of day to a session based on filename cues."""
    fn_lower = filename.lower()
    for cue, (h, m) in TIME_CUES.items():
        if cue in fn_lower:
            return date.replace(hour=h, minute=m)

    # Default: hash the filename to spread sessions across the day
    hash_val = hash(filename) % 4
    hours = [9, 12, 15, 20]
    return date.replace(hour=hours[hash_val], minute=0)


# ─── Trace creation ─────────────────────────────────────────────

def session_to_traces(parsed: dict) -> list[Trace]:
    """Convert a parsed session file into a list of Trace objects.

    Each section becomes 1+ traces. Traces within a session are
    linked via parent_trace_id for temporal threading.
    """
    conversation_id = str(uuid.uuid4())
    base_time = assign_base_time(parsed["filename"], parsed["date"])
    traces = []
    minute_offset = 0

    for section in parsed["sections"]:
        chunks = chunk_content(section["content"])

        for chunk in chunks:
            trace_time = base_time + timedelta(minutes=minute_offset)
            parent_id = traces[-1].id if traces else None

            trace = Trace(
                id=str(uuid.uuid4()),
                timestamp=trace_time.isoformat(),
                content=chunk,
                conversation_id=conversation_id,
                parent_trace_id=parent_id,
                source=section["source"],
            )
            traces.append(trace)
            minute_offset += 2  # 2 minutes between traces

    return traces


# ─── Main seeding logic ─────────────────────────────────────────

def seed_database(
    sessions_dir: str,
    db_path: str = "./data/voku.db",
    max_files: int | None = None,
    dry_run: bool = False,
    skip_annotations: bool = True,
    wipe: bool = False,
    include_references: bool = False,
):
    """Main entry point: read session logs, create traces, embed, connect."""

    # Optionally wipe existing data
    if wipe and not dry_run:
        import sqlite3
        print(f"Wiping existing data from {db_path}...")
        conn = sqlite3.connect(db_path)
        for table in ["traces", "embeddings", "annotations", "connections", "resources"]:
            try:
                conn.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError:
                pass  # Table might not exist yet
        conn.commit()
        conn.close()
        print("  ✓ Database wiped")

    # Discover session files
    pattern = os.path.join(sessions_dir, "*.md")
    files = sorted(glob.glob(pattern))

    # Also include references directory if requested
    if include_references:
        refs_dir = os.path.join(os.path.dirname(sessions_dir), "references")
        if os.path.isdir(refs_dir):
            ref_files = sorted(glob.glob(os.path.join(refs_dir, "*.md")))
            # References don't have date prefixes — add them as recent traces
            # We'll handle these specially in parse_session_file
            files.extend(ref_files)
            print(f"  + {len(ref_files)} reference files from {refs_dir}")

    # Filter out non-session files (CLOSEOUT, SYNC, tracker files) from sessions dir only
    session_files = [f for f in files if re.match(r".*\d{4}-\d{2}-\d{2}_", os.path.basename(f))]
    ref_files_list = [f for f in files if f not in session_files]
    files = session_files + ref_files_list  # Keep references that were explicitly added

    if max_files:
        files = files[:max_files]

    print(f"Found {len(files)} session files in {sessions_dir}")

    # Parse all files
    all_traces = []
    domain_counts = {}
    file_count = 0

    for filepath in files:
        parsed = parse_session_file(filepath)
        if parsed is None or not parsed["sections"]:
            continue

        traces = session_to_traces(parsed)
        if not traces:
            continue

        # Classify domain for stats
        full_text = " ".join(t.content for t in traces)
        domain = classify_domain(full_text)
        domain_counts[domain] = domain_counts.get(domain, 0) + len(traces)

        all_traces.extend(traces)
        file_count += 1

    print(f"\nParsed {file_count} files → {len(all_traces)} traces")
    print(f"\nDomain distribution:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"  {domain:15s} {count:4d} traces")

    if dry_run:
        print("\n[DRY RUN] No database changes made.")
        return

    # Initialize storage + embedder
    print(f"\nInitializing storage at {db_path}...")
    storage = SQLiteTraceStorage(db_path)
    print("Loading BGE embedding model (first run downloads ~420MB)...")
    embedder = BGEBaseEmbedding()

    # Store traces
    print(f"\nStoring {len(all_traces)} traces...")
    for i, trace in enumerate(all_traces):
        storage.store_trace(trace)
        if (i + 1) % 100 == 0:
            print(f"  stored {i + 1}/{len(all_traces)}")
    print(f"  ✓ {len(all_traces)} traces stored")

    # Batch embed
    print(f"\nEmbedding {len(all_traces)} traces (batch)...")
    contents = [t.content for t in all_traces]
    batch_size = 64
    for start in range(0, len(contents), batch_size):
        end = min(start + batch_size, len(contents))
        batch_texts = contents[start:end]
        batch_traces = all_traces[start:end]
        embeddings = embedder.embed_batch(batch_texts)
        for trace, emb in zip(batch_traces, embeddings):
            storage.store_embedding(trace.id, emb, embedder.model_name)
        print(f"  embedded {end}/{len(all_traces)}")
    print(f"  ✓ {len(all_traces)} embeddings stored")

    # Compute connections
    print(f"\nComputing connections...")
    conn_service = ConnectionService(storage)
    counts = conn_service.compute_all(k=5, threshold=0.3)
    print(f"  ✓ temporal: {counts['temporal']}, semantic: {counts['semantic']}")

    # Optional: annotation extraction (requires Groq API)
    if not skip_annotations:
        print(f"\nExtracting annotations (requires Groq API key)...")
        try:
            import asyncio
            from app.services.annotation import AnnotationExtractionService
            from app.services.router import get_provider

            provider = get_provider()
            ann_service = AnnotationExtractionService(provider)

            async def extract_all():
                total_annotations = 0
                for i, trace in enumerate(all_traces):
                    if trace.source == "assistant":
                        continue  # Only annotate user traces
                    # Get conversation context
                    conv_traces = storage.get_traces_by_conversation(trace.conversation_id)
                    idx = next((j for j, t in enumerate(conv_traces) if t.id == trace.id), 0)
                    context = conv_traces[max(0, idx - 4):idx]

                    annotations = await ann_service.extract(trace, context)
                    for ann in annotations:
                        storage.store_annotation(ann)
                    total_annotations += len(annotations)

                    if (i + 1) % 50 == 0:
                        print(f"  annotated {i + 1}/{len(all_traces)} ({total_annotations} annotations)")
                return total_annotations

            total = asyncio.run(extract_all())
            print(f"  ✓ {total} annotations extracted")

        except Exception as e:
            print(f"  ⚠ Annotation extraction failed: {e}")
            print(f"    Run again later with Groq API key configured.")

    # Summary
    print(f"\n{'='*50}")
    print(f"SEED COMPLETE")
    print(f"{'='*50}")
    print(f"  Traces:      {len(all_traces)}")
    print(f"  Embeddings:  {len(all_traces)}")
    print(f"  Temporal:    {counts['temporal']} connections")
    print(f"  Semantic:    {counts['semantic']} connections")
    print(f"  Files:       {file_count}")
    print(f"  Domains:     {len(domain_counts)}")
    print(f"  DB:          {db_path}")
    print(f"{'='*50}")

    storage.close()


# ─── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed Voku database from vault session logs"
    )
    parser.add_argument(
        "--sessions-dir",
        required=True,
        help="Path to vault session logs directory (brain/sessions/)",
    )
    parser.add_argument(
        "--db-path",
        default="./data/voku.db",
        help="Path to voku.db (default: ./data/voku.db)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Max number of session files to process (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print stats without writing to DB",
    )
    parser.add_argument(
        "--skip-annotations",
        action="store_true",
        default=True,
        help="Skip LLM annotation extraction (default: True)",
    )
    parser.add_argument(
        "--with-annotations",
        action="store_true",
        help="Run LLM annotation extraction (requires Groq API key)",
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Wipe existing DB data before seeding (fresh start)",
    )
    parser.add_argument(
        "--include-references",
        action="store_true",
        help="Also include brain/references/ directory as source material",
    )

    args = parser.parse_args()

    # --with-annotations overrides --skip-annotations
    skip_ann = not args.with_annotations

    seed_database(
        sessions_dir=args.sessions_dir,
        db_path=args.db_path,
        max_files=args.max_files,
        dry_run=args.dry_run,
        skip_annotations=skip_ann,
        wipe=args.wipe,
        include_references=args.include_references,
    )
