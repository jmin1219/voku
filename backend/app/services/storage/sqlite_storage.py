"""
SQLite storage implementation. Single file, numpy for vector search.

Component 1.2 in COMPONENT_SPEC.md.
Vector strategy: load all embeddings into memory on startup, cosine similarity via numpy.
At 50K propositions × 768 dims: ~150MB memory, <15ms search.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np

from . import StorageService
from .models import StoredProposition, SimilarResult


class SQLiteStorage(StorageService):
    """SQLite implementation. Single file, numpy for vector search."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        # In-memory embedding cache for fast vector search
        self._embedding_ids: list[str] = []
        self._embedding_matrix: np.ndarray | None = None
        self._load_embeddings_cache()

    def _init_db(self):
        """Create tables if they don't exist."""
        self._conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA busy_timeout=5000;
            PRAGMA foreign_keys=ON;
            PRAGMA cache_size=-64000;

            CREATE TABLE IF NOT EXISTS propositions (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                node_type TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                source_type TEXT DEFAULT 'conversation',
                source_char_start INTEGER,
                source_char_end INTEGER,
                source_file TEXT,
                created_at TEXT NOT NULL,
                session_id TEXT,
                message_index INTEGER,
                domain_tags TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                proposition_id TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                model TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                FOREIGN KEY (proposition_id) REFERENCES propositions(id)
            );

            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                confidence REAL,
                created_at TEXT NOT NULL,
                created_by TEXT DEFAULT 'process_v1',
                FOREIGN KEY (source_id) REFERENCES propositions(id),
                FOREIGN KEY (target_id) REFERENCES propositions(id)
            );
        """)
        self._conn.commit()

    def _load_embeddings_cache(self):
        """Load all embeddings into memory for numpy vector search."""
        rows = self._conn.execute(
            "SELECT proposition_id, embedding, dimensions FROM embeddings"
        ).fetchall()

        if not rows:
            self._embedding_ids = []
            self._embedding_matrix = None
            return

        self._embedding_ids = [row["proposition_id"] for row in rows]
        vectors = [
            np.frombuffer(row["embedding"], dtype=np.float32)
            for row in rows
        ]
        self._embedding_matrix = np.vstack(vectors)

    def _row_to_proposition(self, row: sqlite3.Row) -> StoredProposition:
        """Convert a database row to a StoredProposition."""
        return StoredProposition(
            id=row["id"],
            text=row["text"],
            node_type=row["node_type"],
            confidence=row["confidence"],
            source_type=row["source_type"],
            created_at=row["created_at"],
            session_id=row["session_id"],
            message_index=row["message_index"],
            source_char_start=row["source_char_start"],
            source_char_end=row["source_char_end"],
            source_file=row["source_file"],
            domain_tags=json.loads(row["domain_tags"]),
            status=row["status"],
        )

    def store_proposition(self, proposition: StoredProposition) -> str:
        """Store a proposition. Returns its ID."""
        self._conn.execute(
            """INSERT INTO propositions
            (id, text, node_type, confidence, source_type, source_char_start,
             source_char_end, source_file, created_at, session_id, message_index,
             domain_tags, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                proposition.id,
                proposition.text,
                proposition.node_type,
                proposition.confidence,
                proposition.source_type,
                proposition.source_char_start,
                proposition.source_char_end,
                proposition.source_file,
                proposition.created_at,
                proposition.session_id,
                proposition.message_index,
                json.dumps(proposition.domain_tags),
                proposition.status,
            ),
        )
        self._conn.commit()
        return proposition.id

    def store_embedding(self, proposition_id: str, embedding: np.ndarray, model: str) -> None:
        """Store an embedding and update the in-memory cache."""
        blob = embedding.astype(np.float32).tobytes()
        self._conn.execute(
            "INSERT OR REPLACE INTO embeddings (proposition_id, embedding, model, dimensions) VALUES (?, ?, ?, ?)",
            (proposition_id, blob, model, len(embedding)),
        )
        self._conn.commit()

        # Update in-memory cache (append, don't reload)
        self._embedding_ids.append(proposition_id)
        vec = embedding.astype(np.float32).reshape(1, -1)
        if self._embedding_matrix is None:
            self._embedding_matrix = vec
        else:
            self._embedding_matrix = np.vstack([self._embedding_matrix, vec])

    def find_similar(self, embedding: np.ndarray, threshold: float = 0.85, limit: int = 10) -> list[SimilarResult]:
        """Find propositions with cosine similarity above threshold."""
        if self._embedding_matrix is None or len(self._embedding_ids) == 0:
            return []

        # Cosine similarity: normalize query and corpus, then dot product
        query_norm = embedding / (np.linalg.norm(embedding) + 1e-10)
        corpus_norms = self._embedding_matrix / (
            np.linalg.norm(self._embedding_matrix, axis=1, keepdims=True) + 1e-10
        )
        scores = corpus_norms @ query_norm

        # Filter by threshold, sort descending, limit
        mask = scores >= threshold
        if not mask.any():
            return []

        indices = np.where(mask)[0]
        matched_scores = scores[indices]
        sorted_order = np.argsort(matched_scores)[::-1][:limit]

        results = []
        for idx in sorted_order:
            prop_id = self._embedding_ids[indices[idx]]
            row = self._conn.execute(
                "SELECT * FROM propositions WHERE id = ?", (prop_id,)
            ).fetchone()
            if row:
                results.append(
                    SimilarResult(
                        proposition=self._row_to_proposition(row),
                        score=float(matched_scores[idx]),
                    )
                )
        return results

    def find_by_timerange(self, start: datetime, end: datetime) -> list[StoredProposition]:
        """Find propositions created within a time range."""
        rows = self._conn.execute(
            "SELECT * FROM propositions WHERE created_at >= ? AND created_at <= ? ORDER BY created_at",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [self._row_to_proposition(row) for row in rows]

    def find_by_session(self, session_id: str) -> list[StoredProposition]:
        """Find all propositions from a specific conversation session."""
        rows = self._conn.execute(
            "SELECT * FROM propositions WHERE session_id = ? ORDER BY message_index",
            (session_id,),
        ).fetchall()
        return [self._row_to_proposition(row) for row in rows]

    def get_all_embeddings(self) -> tuple[list[str], np.ndarray]:
        """Load all embeddings. Returns (ids, embedding_matrix)."""
        if self._embedding_matrix is None:
            return [], np.array([], dtype=np.float32)
        return self._embedding_ids.copy(), self._embedding_matrix.copy()

    def close(self):
        """Close the database connection."""
        self._conn.close()
