"""
Piece 0: DB Consolidation — merge two SQLite databases into one.

Before:
  data/voku.db              → conversations (15 rows), messages (31 rows)
  data/m2_conversation.db   → propositions (425), embeddings (425), edges (0)

After:
  data/voku.db              → all 5 tables in one file
  data/archive/             → old files moved here

Strategy:
  Copy conversations + messages INTO m2_conversation.db (the bigger DB),
  then rename m2_conversation.db → voku.db. This avoids touching the
  proposition/embedding blobs — they stay in place, zero risk of corruption.

Usage:
  cd backend
  python -m migrations.consolidate_db

  --dry-run flag prints counts without modifying anything.
"""

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONVERSATIONS_DB = DATA_DIR / "voku.db"
PROPOSITIONS_DB = DATA_DIR / "m2_conversation.db"
ARCHIVE_DIR = DATA_DIR / "archive"

# Stale files to archive alongside the originals
STALE_FILES = [
    "m2_conv_retest.db",
    "m2_conv_test.db",
    "m2_v2.db",
    "ingest_log.txt",
]


def get_row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Return {table_name: row_count} for all tables in the database."""
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    counts = {}
    for (name,) in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
        counts[name] = count
    return counts


def validate_source_dbs():
    """Check both source databases exist and have expected tables."""
    if not CONVERSATIONS_DB.exists():
        sys.exit(f"ERROR: {CONVERSATIONS_DB} not found")
    if not PROPOSITIONS_DB.exists():
        sys.exit(f"ERROR: {PROPOSITIONS_DB} not found")

    # Check conversations DB has the tables we expect
    conn = sqlite3.connect(str(CONVERSATIONS_DB))
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    if "conversations" not in tables or "messages" not in tables:
        sys.exit(f"ERROR: {CONVERSATIONS_DB} missing conversations/messages tables")

    # Check propositions DB has its tables
    conn = sqlite3.connect(str(PROPOSITIONS_DB))
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    if "propositions" not in tables:
        sys.exit(f"ERROR: {PROPOSITIONS_DB} missing propositions table")


def copy_conversations_into_propositions_db(dry_run: bool = False):
    """
    Create conversations + messages tables in m2_conversation.db,
    then copy all rows from voku.db into them.
    """
    # Read source data first
    src = sqlite3.connect(str(CONVERSATIONS_DB))
    src.row_factory = sqlite3.Row

    conversations = src.execute("SELECT * FROM conversations").fetchall()
    messages = src.execute("SELECT * FROM messages").fetchall()
    src.close()

    print(f"Source (voku.db): {len(conversations)} conversations, {len(messages)} messages")

    if dry_run:
        return len(conversations), len(messages)

    # Open target and create tables
    dst = sqlite3.connect(str(PROPOSITIONS_DB))

    dst.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            thinking TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
    """)

    # Insert rows
    for row in conversations:
        dst.execute(
            "INSERT OR IGNORE INTO conversations (id, created_at, updated_at) VALUES (?, ?, ?)",
            (row["id"], row["created_at"], row["updated_at"]),
        )

    for row in messages:
        dst.execute(
            "INSERT OR IGNORE INTO messages (id, conversation_id, role, content, created_at, thinking) VALUES (?, ?, ?, ?, ?, ?)",
            (row["id"], row["conversation_id"], row["role"], row["content"], row["created_at"], row["thinking"]),
        )

    dst.commit()

    # Force WAL checkpoint — flush all WAL data into the main DB file.
    # Without this, INSERT data lives in the .db-wal file and gets lost
    # when we delete WAL/SHM files before the rename.
    dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    # Verify
    verify_convs = dst.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    verify_msgs = dst.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    dst.close()

    print(f"Target (m2_conversation.db): {verify_convs} conversations, {verify_msgs} messages")

    if verify_convs != len(conversations):
        sys.exit(f"MISMATCH: expected {len(conversations)} conversations, got {verify_convs}")
    if verify_msgs != len(messages):
        sys.exit(f"MISMATCH: expected {len(messages)} messages, got {verify_msgs}")

    return verify_convs, verify_msgs


def archive_and_rename(dry_run: bool = False):
    """
    Move old files to archive/, rename m2_conversation.db → voku.db.
    Also archives WAL/SHM files if present.
    """
    ARCHIVE_DIR.mkdir(exist_ok=True)

    if dry_run:
        print(f"\n[DRY RUN] Would archive old files to {ARCHIVE_DIR}")
        print(f"[DRY RUN] Would rename m2_conversation.db → voku.db")
        return

    # Archive the old voku.db (conversations-only version)
    if CONVERSATIONS_DB.exists():
        shutil.move(str(CONVERSATIONS_DB), str(ARCHIVE_DIR / "voku_conversations_only.db"))
        print(f"Archived old voku.db → archive/voku_conversations_only.db")

    # Archive stale files
    for name in STALE_FILES:
        path = DATA_DIR / name
        if path.exists():
            shutil.move(str(path), str(ARCHIVE_DIR / name))
            print(f"Archived {name}")

    # Archive WAL/SHM files for m2_conversation.db (SQLite temp files)
    for suffix in ["-wal", "-shm"]:
        wal_path = DATA_DIR / f"m2_conversation.db{suffix}"
        if wal_path.exists():
            wal_path.unlink()
            print(f"Removed m2_conversation.db{suffix}")

    # The rename: m2_conversation.db → voku.db
    shutil.move(str(PROPOSITIONS_DB), str(DATA_DIR / "voku.db"))
    print(f"Renamed m2_conversation.db → voku.db")


def verify_final_db():
    """Verify the consolidated voku.db has all expected tables and data."""
    final_db = DATA_DIR / "voku.db"
    if not final_db.exists():
        sys.exit("ERROR: Final voku.db not found after rename")

    conn = sqlite3.connect(str(final_db))
    counts = get_row_counts(conn)
    conn.close()

    print(f"\n=== Final voku.db ===")
    for table, count in sorted(counts.items()):
        print(f"  {table}: {count} rows")

    expected_tables = {"propositions", "embeddings", "edges", "conversations", "messages"}
    missing = expected_tables - set(counts.keys())
    if missing:
        sys.exit(f"ERROR: Missing tables in final DB: {missing}")

    print("\n✅ Consolidation complete. All 5 tables present.")


def main():
    parser = argparse.ArgumentParser(description="Consolidate Voku databases")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without modifying files")
    args = parser.parse_args()

    print("=== Voku DB Consolidation (Piece 0) ===\n")

    # Step 1: Validate
    validate_source_dbs()

    # Show current state
    print("--- Before ---")
    conn = sqlite3.connect(str(CONVERSATIONS_DB))
    for table, count in get_row_counts(conn).items():
        print(f"  voku.db → {table}: {count}")
    conn.close()

    conn = sqlite3.connect(str(PROPOSITIONS_DB))
    for table, count in get_row_counts(conn).items():
        print(f"  m2_conversation.db → {table}: {count}")
    conn.close()
    print()

    # Step 2: Copy conversations into propositions DB
    copy_conversations_into_propositions_db(dry_run=args.dry_run)

    # Step 3: Archive old files, rename
    archive_and_rename(dry_run=args.dry_run)

    # Step 4: Verify
    if not args.dry_run:
        verify_final_db()
    else:
        print("\n[DRY RUN] No files modified. Run without --dry-run to execute.")


if __name__ == "__main__":
    main()
