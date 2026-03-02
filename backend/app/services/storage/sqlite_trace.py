"""
SQLite trace storage — single file, numpy vector search.

v2 replaces SQLiteStorage (propositions) + ConversationService (messages)
with a unified trace-based implementation. One table, one service.

Vector strategy: load all embeddings into memory on startup, cosine
similarity via numpy. At 10K traces × 768 dims: ~30MB memory, <10ms search.

Design: SPEC.md § Data Model, CARRY_FORWARD.md § Backend File Map
Constraint 3.13: Single-file SQLite database.
Constraint 3.14: Implements TraceStorageService ABC.
"""

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

from . import TraceStorageService
from .models import Annotation, Connection, Trace, SimilarTrace


class SQLiteTraceStorage(TraceStorageService):
    """SQLite trace storage with in-memory embedding cache.

    Manages traces (immutable ground truth) and their embeddings.
    Conversations are implicit groupings via conversation_id — no
    separate conversations table.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_pragmas()
        self._ensure_schema()
        # In-memory embedding cache for fast vector search
        self._embedding_ids: list[str] = []
        self._embedding_matrix: np.ndarray | None = None
        self._cache_lock = threading.Lock()
        self._load_embeddings_cache()

    def _init_pragmas(self):
        """Set SQLite performance and safety pragmas."""
        self._conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA busy_timeout=5000;
            PRAGMA foreign_keys=ON;
            PRAGMA cache_size=-64000;
        """)

    def _ensure_schema(self):
        """Create tables if they don't exist. Runs v2_schema.sql."""
        from pathlib import Path
        schema_path = Path(__file__).parent.parent.parent / "migrations" / "v2_schema.sql"
        if schema_path.exists():
            self._conn.executescript(schema_path.read_text())
        else:
            # Fallback: minimal schema for tests that don't have migrations dir
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS traces (
                    id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, content TEXT NOT NULL,
                    conversation_id TEXT, parent_trace_id TEXT, source TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS annotations (
                    id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, type TEXT NOT NULL,
                    key TEXT, value TEXT, confidence REAL, extracted_at TEXT NOT NULL, extractor TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS connections (
                    source_id TEXT NOT NULL, target_id TEXT NOT NULL, type TEXT NOT NULL,
                    weight REAL, created_at TEXT NOT NULL, PRIMARY KEY (source_id, target_id, type)
                );
                CREATE TABLE IF NOT EXISTS resources (
                    id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, type TEXT NOT NULL,
                    uri TEXT, relationship TEXT DEFAULT 'encountered', summary TEXT
                );
                CREATE TABLE IF NOT EXISTS embeddings (
                    trace_id TEXT PRIMARY KEY, model TEXT NOT NULL, vector BLOB NOT NULL, computed_at TEXT NOT NULL
                );
            """)

    def _load_embeddings_cache(self):
        """Load all embeddings into memory for numpy vector search.

        Called once at init. After that, store_embedding() appends
        incrementally — no full reload needed during a session.
        """
        rows = self._conn.execute(
            "SELECT trace_id, vector FROM embeddings"
        ).fetchall()

        if not rows:
            self._embedding_ids = []
            self._embedding_matrix = None
            return

        self._embedding_ids = [row["trace_id"] for row in rows]
        vectors = [
            np.frombuffer(row["vector"], dtype=np.float32)
            for row in rows
        ]
        self._embedding_matrix = np.vstack(vectors)

    # ------------------------------------------------------------------
    # Row conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_trace(row: sqlite3.Row) -> Trace:
        """Convert a database row to a Trace dataclass."""
        return Trace(
            id=row["id"],
            timestamp=row["timestamp"],
            content=row["content"],
            conversation_id=row["conversation_id"],
            parent_trace_id=row["parent_trace_id"],
            source=row["source"],
        )

    # ------------------------------------------------------------------
    # Trace CRUD
    # ------------------------------------------------------------------

    def store_trace(self, trace: Trace) -> str:
        """Store an immutable trace. Returns its ID."""
        self._conn.execute(
            """INSERT INTO traces
               (id, timestamp, content, conversation_id, parent_trace_id, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                trace.id,
                trace.timestamp,
                trace.content,
                trace.conversation_id,
                trace.parent_trace_id,
                trace.source,
            ),
        )
        self._conn.commit()
        return trace.id

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Retrieve a single trace by ID. Returns None if not found."""
        row = self._conn.execute(
            "SELECT * FROM traces WHERE id = ?", (trace_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_trace(row)

    def get_traces_by_conversation(self, conversation_id: str) -> list[Trace]:
        """Get all traces in a conversation, ordered by timestamp ascending."""
        rows = self._conn.execute(
            "SELECT * FROM traces WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conversation_id,),
        ).fetchall()
        return [self._row_to_trace(row) for row in rows]

    # ------------------------------------------------------------------
    # Conversation listing
    # ------------------------------------------------------------------

    def list_conversations(self) -> list[dict]:
        """List all conversations derived from trace groupings.

        Returns dicts with id, first_trace_at, last_trace_at, trace_count.
        Ordered by most recent activity first.
        Excludes traces with no conversation_id (system/orphan traces).
        """
        rows = self._conn.execute(
            """SELECT
                   conversation_id AS id,
                   MIN(timestamp) AS first_trace_at,
                   MAX(timestamp) AS last_trace_at,
                   COUNT(*) AS trace_count
               FROM traces
               WHERE conversation_id IS NOT NULL
               GROUP BY conversation_id
               ORDER BY last_trace_at DESC"""
        ).fetchall()
        return [
            {
                "id": row["id"],
                "first_trace_at": row["first_trace_at"],
                "last_trace_at": row["last_trace_at"],
                "trace_count": row["trace_count"],
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------

    def store_annotation(self, annotation: Annotation) -> str:
        """Store a computed annotation on a trace. Returns its ID."""
        self._conn.execute(
            """INSERT INTO annotations
               (id, trace_id, type, key, value, confidence, extracted_at, extractor)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                annotation.id,
                annotation.trace_id,
                annotation.type,
                annotation.key,
                annotation.value,
                annotation.confidence,
                annotation.extracted_at,
                annotation.extractor,
            ),
        )
        self._conn.commit()
        return annotation.id

    def get_annotations_for_trace(self, trace_id: str) -> list[Annotation]:
        """Get all annotations for a trace, ordered by extracted_at."""
        rows = self._conn.execute(
            "SELECT * FROM annotations WHERE trace_id = ? ORDER BY extracted_at ASC",
            (trace_id,),
        ).fetchall()
        return [self._row_to_annotation(row) for row in rows]

    def get_annotations_by_type(self, annotation_type: str) -> list[Annotation]:
        """Get all annotations of a given type across all traces."""
        rows = self._conn.execute(
            "SELECT * FROM annotations WHERE type = ? ORDER BY extracted_at ASC",
            (annotation_type,),
        ).fetchall()
        return [self._row_to_annotation(row) for row in rows]

    @staticmethod
    def _row_to_annotation(row: sqlite3.Row) -> Annotation:
        """Convert a database row to an Annotation dataclass."""
        return Annotation(
            id=row["id"],
            trace_id=row["trace_id"],
            type=row["type"],
            key=row["key"],
            value=row["value"],
            confidence=row["confidence"],
            extracted_at=row["extracted_at"],
            extractor=row["extractor"],
        )

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------

    def store_connection(self, connection: Connection) -> None:
        """Store a connection. INSERT OR REPLACE for recomputation."""
        self._conn.execute(
            """INSERT OR REPLACE INTO connections
               (source_id, target_id, type, weight, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                connection.source_id,
                connection.target_id,
                connection.type,
                connection.weight,
                connection.created_at,
            ),
        )
        self._conn.commit()

    def get_connections_for_trace(self, trace_id: str) -> list[Connection]:
        """Get all connections where trace_id is source OR target."""
        rows = self._conn.execute(
            """SELECT * FROM connections
               WHERE source_id = ? OR target_id = ?
               ORDER BY created_at ASC""",
            (trace_id, trace_id),
        ).fetchall()
        return [self._row_to_connection(row) for row in rows]

    def get_connections_by_type(self, connection_type: str) -> list[Connection]:
        """Get all connections of a given type."""
        rows = self._conn.execute(
            "SELECT * FROM connections WHERE type = ? ORDER BY created_at ASC",
            (connection_type,),
        ).fetchall()
        return [self._row_to_connection(row) for row in rows]

    def delete_connections_by_type(self, connection_type: str) -> int:
        """Delete all connections of a given type. Returns count deleted."""
        cursor = self._conn.execute(
            "DELETE FROM connections WHERE type = ?",
            (connection_type,),
        )
        self._conn.commit()
        return cursor.rowcount

    @staticmethod
    def _row_to_connection(row: sqlite3.Row) -> Connection:
        """Convert a database row to a Connection dataclass."""
        return Connection(
            source_id=row["source_id"],
            target_id=row["target_id"],
            type=row["type"],
            weight=row["weight"],
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # Embeddings + vector search
    # ------------------------------------------------------------------

    def store_embedding(
        self, trace_id: str, embedding: np.ndarray, model: str
    ) -> None:
        """Store an embedding and update the in-memory cache.

        Uses INSERT OR REPLACE to support re-embedding with better models.
        Cache is updated incrementally — no full reload.
        """
        blob = embedding.astype(np.float32).tobytes()
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT OR REPLACE INTO embeddings
               (trace_id, model, vector, computed_at)
               VALUES (?, ?, ?, ?)""",
            (trace_id, model, blob, now),
        )
        self._conn.commit()

        # Update in-memory cache (lock protects concurrent read/write)
        with self._cache_lock:
            if trace_id in self._embedding_ids:
                # Re-embedding: replace in-place
                idx = self._embedding_ids.index(trace_id)
                self._embedding_matrix[idx] = embedding.astype(np.float32)
            else:
                # New embedding: append
                self._embedding_ids.append(trace_id)
                vec = embedding.astype(np.float32).reshape(1, -1)
                if self._embedding_matrix is None:
                    self._embedding_matrix = vec
                else:
                    self._embedding_matrix = np.vstack(
                        [self._embedding_matrix, vec]
                    )

    def find_similar(
        self,
        embedding: np.ndarray,
        threshold: float = 0.35,
        limit: int = 10,
    ) -> list[SimilarTrace]:
        """Find traces with cosine similarity above threshold.

        Returns results sorted by similarity descending, capped at limit.
        Uses in-memory cache — no disk reads during search.
        """
        with self._cache_lock:
            if self._embedding_matrix is None or len(self._embedding_ids) == 0:
                return []

            # Cosine similarity: normalize then dot product
            query_norm = embedding / (np.linalg.norm(embedding) + 1e-10)
            corpus_norms = self._embedding_matrix / (
                np.linalg.norm(self._embedding_matrix, axis=1, keepdims=True)
                + 1e-10
            )
            scores = corpus_norms @ query_norm

            # Filter by threshold
            mask = scores >= threshold
            if not mask.any():
                return []

            # Sort descending, cap at limit
            indices = np.where(mask)[0]
            matched_scores = scores[indices]
            sorted_order = np.argsort(matched_scores)[::-1][:limit]

            # Collect matched trace IDs and scores while holding lock
            matches = []
            for idx in sorted_order:
                matches.append((
                    self._embedding_ids[indices[idx]],
                    float(matched_scores[idx]),
                ))

        # Fetch full trace data outside lock (DB reads are thread-safe via SQLite WAL)
        results = []
        for trace_id, score in matches:
            trace = self.get_trace(trace_id)
            if trace is not None:
                results.append(SimilarTrace(trace=trace, score=score))
        return results

    def get_all_embeddings(self) -> tuple[list[str], np.ndarray]:
        """Return all embeddings from cache. (ids, matrix) or ([], empty)."""
        with self._cache_lock:
            if self._embedding_matrix is None:
                return [], np.array([], dtype=np.float32)
            return self._embedding_ids.copy(), self._embedding_matrix.copy()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """Close the database connection."""
        self._conn.close()
