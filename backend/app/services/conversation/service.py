import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import Conversation, Message


class ConversationService:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        self._conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA busy_timeout=5000;
            PRAGMA foreign_keys=ON;
            PRAGMA cache_size=-64000;

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
        self._conn.commit()

    def _current_time(self) -> str:
        """Get the current time as an ISO string."""
        return datetime.now(timezone.utc).isoformat()

    def _row_to_conversation(self, row: sqlite3.Row) -> Conversation:
        """Convert a database row to a Conversation object."""
        return Conversation(
            id=row["id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """Convert a database row to a Message object."""
        return Message(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"],
            thinking=row["thinking"],
        )

    def create_conversation(self):
        """Create a new conversation."""
        conversation_id = str(uuid.uuid4())
        now = self._current_time()
        self._conn.execute(
            """
            INSERT INTO conversations (id, created_at, updated_at)
            VALUES (?, ?, ?)
        """,
            (conversation_id, now, now),
        )
        self._conn.commit()
        return Conversation(id=conversation_id, created_at=now, updated_at=now)

    def add_message(
        self, conversation_id: str, role: str, content: str, thinking: str | None = None
    ):
        """Add a message to a conversation."""
        message_id = str(uuid.uuid4())
        now = self._current_time()
        self._conn.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, created_at, thinking)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (message_id, conversation_id, role, content, now, thinking),
        )
        self._conn.execute(
            """
            UPDATE conversations SET updated_at = ? WHERE id = ?
        """,
            (now, conversation_id),
        )
        self._conn.commit()
        return Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=now,
            thinking=thinking,
        )

    def get_conversation_messages(self, conversation_id: str) -> list[Message]:
        """Get all messages for a conversation."""
        rows = self._conn.execute(
            """
            SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC
        """,
            (conversation_id,),
        ).fetchall()
        return [self._row_to_message(row) for row in rows]

    def list_conversations(self) -> list[Conversation]:
        """List all conversations."""
        rows = self._conn.execute(
            """
            SELECT * FROM conversations ORDER BY updated_at DESC
        """,
        ).fetchall()
        return [self._row_to_conversation(row) for row in rows]

    def close(self):
        """Close the database connection."""
        self._conn.close()
