"""
UserModelStorage — CRUD for user_model and model_evidence tables.

Piece 1 of Build 4. Manages the inference layer that sits above propositions.
Shares the same SQLite database as propositions (after Piece 0 consolidation).

Tables:
  user_model     — dimensions with estimates, confidence, lifecycle state
  model_evidence — junction linking propositions to dimensions with relevance/direction
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class UserModelRow:
    id: str
    dimension: str
    subdimension: str | None
    description: str
    estimate: str
    confidence: float
    uncertainty_type: str  # sparse | conflicted | stable
    evidence_count: int
    last_updated: str
    last_evidence_at: str | None
    decay_class: str  # core | preference | situational
    decay_rate: float | None
    goal_relevance: list[str] = field(default_factory=list)
    status: str = "active"
    proposed_from: str | None = None
    parent_id: str | None = None
    summary_history: list[dict] = field(default_factory=list)
    reasoning_trace: str | None = None


@dataclass
class EvidenceRow:
    model_id: str
    proposition_id: str
    relevance: float
    direction: str  # supports | contradicts | contextualizes
    assigned_at: str
    assigned_by: str  # exhale | manual | extraction


class UserModelStorage:
    """SQLite storage for user model dimensions and evidence mappings."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()

    def _init_tables(self):
        """Create user_model and model_evidence tables if they don't exist."""
        self._conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA busy_timeout=5000;
            PRAGMA cache_size=-64000;

            CREATE TABLE IF NOT EXISTS user_model (
                id TEXT PRIMARY KEY,
                dimension TEXT NOT NULL,
                subdimension TEXT,
                description TEXT NOT NULL,
                estimate TEXT NOT NULL,
                confidence REAL NOT NULL,
                uncertainty_type TEXT DEFAULT 'sparse',
                evidence_count INTEGER DEFAULT 0,
                last_updated TEXT NOT NULL,
                last_evidence_at TEXT,
                decay_class TEXT NOT NULL,
                decay_rate REAL,
                goal_relevance TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                proposed_from TEXT,
                parent_id TEXT,
                summary_history TEXT DEFAULT '[]',
                reasoning_trace TEXT
            );

            CREATE TABLE IF NOT EXISTS model_evidence (
                model_id TEXT NOT NULL,
                proposition_id TEXT NOT NULL,
                relevance REAL DEFAULT 0.5,
                direction TEXT DEFAULT 'supports',
                assigned_at TEXT NOT NULL,
                assigned_by TEXT DEFAULT 'exhale',
                PRIMARY KEY (model_id, proposition_id),
                FOREIGN KEY (model_id) REFERENCES user_model(id),
                FOREIGN KEY (proposition_id) REFERENCES propositions(id)
            );
        """)
        self._conn.commit()

    def add_evidence_mode_column(self):
        """Add evidence_mode column to propositions table (idempotent migration)."""
        # Check if column already exists
        cols = self._conn.execute("PRAGMA table_info(propositions)").fetchall()
        col_names = {c["name"] for c in cols}
        if "evidence_mode" not in col_names:
            self._conn.execute(
                "ALTER TABLE propositions ADD COLUMN evidence_mode TEXT DEFAULT 'experiential'"
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def seed_dimensions(self, config_path: str | Path):
        """Load seed dimensions from JSON config. Idempotent — skips existing IDs.

        Loads from `config_path.local.json` if it exists, else `config_path`.
        """
        config_path = Path(config_path)
        local_path = config_path.with_suffix(".local.json")
        source = local_path if local_path.exists() else config_path

        with open(source) as f:
            seeds = json.load(f)

        now = datetime.now(timezone.utc).isoformat()
        for seed in seeds:
            existing = self._conn.execute(
                "SELECT id FROM user_model WHERE id = ?", (seed["id"],)
            ).fetchone()
            if existing:
                continue

            self._conn.execute(
                """INSERT INTO user_model
                (id, dimension, subdimension, description, estimate, confidence,
                 uncertainty_type, evidence_count, last_updated, decay_class, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    seed["id"],
                    seed["dimension"],
                    seed.get("subdimension"),
                    seed["description"],
                    "",  # empty estimate until first exhale
                    0.0,  # no evidence yet
                    "sparse",
                    0,
                    now,
                    seed["decay_class"],
                    "active",
                ),
            )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def _row_to_model(self, row: sqlite3.Row) -> UserModelRow:
        return UserModelRow(
            id=row["id"],
            dimension=row["dimension"],
            subdimension=row["subdimension"],
            description=row["description"],
            estimate=row["estimate"],
            confidence=row["confidence"],
            uncertainty_type=row["uncertainty_type"],
            evidence_count=row["evidence_count"],
            last_updated=row["last_updated"],
            last_evidence_at=row["last_evidence_at"],
            decay_class=row["decay_class"],
            decay_rate=row["decay_rate"],
            goal_relevance=json.loads(row["goal_relevance"]),
            status=row["status"],
            proposed_from=row["proposed_from"],
            parent_id=row["parent_id"],
            summary_history=json.loads(row["summary_history"]),
            reasoning_trace=row["reasoning_trace"],
        )

    def get_dimension(self, dim_id: str) -> UserModelRow | None:
        row = self._conn.execute(
            "SELECT * FROM user_model WHERE id = ?", (dim_id,)
        ).fetchone()
        return self._row_to_model(row) if row else None

    def get_all_dimensions(self, status: str = "active") -> list[UserModelRow]:
        rows = self._conn.execute(
            "SELECT * FROM user_model WHERE status = ? ORDER BY dimension, subdimension",
            (status,),
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_children(self, parent_id: str) -> list[UserModelRow]:
        rows = self._conn.execute(
            "SELECT * FROM user_model WHERE parent_id = ? AND status = 'active'",
            (parent_id,),
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def update_dimension(
        self,
        dim_id: str,
        estimate: str,
        confidence: float,
        uncertainty_type: str,
        reasoning_trace: str,
        evidence_count: int | None = None,
    ):
        """Update a dimension's estimate. Does NOT append to summary_history
        — caller must check threshold gate and call append_history separately.
        """
        now = datetime.now(timezone.utc).isoformat()
        params: dict = {
            "estimate": estimate,
            "confidence": confidence,
            "uncertainty_type": uncertainty_type,
            "reasoning_trace": reasoning_trace,
            "last_updated": now,
        }
        # Keys are hardcoded above — no injection risk. Dict ordering is stable (Python 3.7+).
        set_clause = ", ".join(f"{k} = ?" for k in params)
        values = list(params.values())

        if evidence_count is not None:
            set_clause += ", evidence_count = ?"
            values.append(evidence_count)

        values.append(dim_id)
        self._conn.execute(
            f"UPDATE user_model SET {set_clause} WHERE id = ?",
            values,
        )
        self._conn.commit()

    def append_history(self, dim_id: str, old_estimate: str, old_confidence: float, timestamp: str):
        """Append a snapshot to summary_history. Only call after threshold gate passes."""
        row = self._conn.execute(
            "SELECT summary_history FROM user_model WHERE id = ?", (dim_id,)
        ).fetchone()
        if not row:
            return
        history = json.loads(row["summary_history"])
        history.append({
            "estimate": old_estimate,
            "confidence": old_confidence,
            "timestamp": timestamp,
        })
        self._conn.execute(
            "UPDATE user_model SET summary_history = ? WHERE id = ?",
            (json.dumps(history), dim_id),
        )
        self._conn.commit()

    def set_last_evidence_at(self, dim_id: str, timestamp: str):
        """Update the last_evidence_at field after new evidence is assigned."""
        self._conn.execute(
            "UPDATE user_model SET last_evidence_at = ? WHERE id = ?",
            (timestamp, dim_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Dimension lifecycle
    # ------------------------------------------------------------------

    def propose_dimension(
        self,
        dim_id: str,
        dimension: str,
        subdimension: str | None,
        description: str,
        proposed_from: str,
        parent_id: str | None = None,
        decay_class: str = "preference",
    ):
        """Insert a proposed dimension (status='proposed'). Idempotent."""
        existing = self._conn.execute(
            "SELECT id FROM user_model WHERE id = ?", (dim_id,)
        ).fetchone()
        if existing:
            return

        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT INTO user_model
            (id, dimension, subdimension, description, estimate, confidence,
             uncertainty_type, evidence_count, last_updated, decay_class,
             status, proposed_from, parent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (dim_id, dimension, subdimension, description,
             "", 0.0, "sparse", 0, now, decay_class,
             "proposed", proposed_from, parent_id),
        )
        self._conn.commit()

    def confirm_dimension(self, dim_id: str):
        self._conn.execute(
            "UPDATE user_model SET status = 'active', proposed_from = NULL WHERE id = ?",
            (dim_id,),
        )
        self._conn.commit()

    def retire_dimension(self, dim_id: str):
        self._conn.execute(
            "UPDATE user_model SET status = 'retired' WHERE id = ?",
            (dim_id,),
        )
        self._conn.commit()

    def rename_dimension(self, dim_id: str, new_description: str):
        self._conn.execute(
            "UPDATE user_model SET description = ? WHERE id = ?",
            (new_description, dim_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Evidence (junction table)
    # ------------------------------------------------------------------

    def store_assignments(self, assignments: list[EvidenceRow]):
        """Batch insert assignments into model_evidence. Skips duplicates."""
        for a in assignments:
            self._conn.execute(
                """INSERT OR IGNORE INTO model_evidence
                (model_id, proposition_id, relevance, direction, assigned_at, assigned_by)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (a.model_id, a.proposition_id, a.relevance, a.direction,
                 a.assigned_at, a.assigned_by),
            )
        self._conn.commit()

        # Update evidence counts and last_evidence_at per dimension
        affected_dims = {a.model_id for a in assignments}
        for dim_id in affected_dims:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM model_evidence WHERE model_id = ?",
                (dim_id,),
            ).fetchone()[0]
            latest = self._conn.execute(
                "SELECT MAX(assigned_at) FROM model_evidence WHERE model_id = ?",
                (dim_id,),
            ).fetchone()[0]
            self._conn.execute(
                "UPDATE user_model SET evidence_count = ?, last_evidence_at = ? WHERE id = ?",
                (count, latest, dim_id),
            )
        self._conn.commit()

    def update_assignment(self, model_id: str, proposition_id: str, relevance: float, direction: str):
        """Update relevance and direction on an existing assignment."""
        self._conn.execute(
            "UPDATE model_evidence SET relevance = ?, direction = ? WHERE model_id = ? AND proposition_id = ?",
            (relevance, direction, model_id, proposition_id),
        )
        self._conn.commit()

    def update_assignments_batch(self, updates: list[tuple[str, str, float, str]]):
        """Batch update relevance and direction. Each tuple: (model_id, proposition_id, relevance, direction)."""
        for model_id, prop_id, relevance, direction in updates:
            self._conn.execute(
                "UPDATE model_evidence SET relevance = ?, direction = ? WHERE model_id = ? AND proposition_id = ?",
                (relevance, direction, model_id, prop_id),
            )
        self._conn.commit()

    def get_all_assignments(self) -> list[dict]:
        """Get all assignments with proposition text, for Pass 2 scoring."""
        rows = self._conn.execute(
            """SELECT me.model_id, me.proposition_id, me.relevance, me.direction,
                      p.text, p.node_type
               FROM model_evidence me
               JOIN propositions p ON me.proposition_id = p.id
               ORDER BY me.model_id, p.created_at""",
        ).fetchall()
        return [
            {
                "model_id": r["model_id"],
                "proposition_id": r["proposition_id"],
                "relevance": r["relevance"],
                "direction": r["direction"],
                "text": r["text"],
                "node_type": r["node_type"],
            }
            for r in rows
        ]

    def get_evidence_for_dimension(self, model_id: str) -> list[dict]:
        """Get all propositions assigned to a dimension, with relevance/direction."""
        rows = self._conn.execute(
            """SELECT me.relevance, me.direction, me.assigned_at,
                      p.id, p.text, p.node_type, p.confidence, p.created_at,
                      p.event_timeframe, p.evidence_mode
               FROM model_evidence me
               JOIN propositions p ON me.proposition_id = p.id
               WHERE me.model_id = ?
               ORDER BY p.created_at""",
            (model_id,),
        ).fetchall()
        return [
            {
                "proposition_id": r["id"],
                "text": r["text"],
                "node_type": r["node_type"],
                "confidence": r["confidence"],
                "created_at": r["created_at"],
                "event_timeframe": r["event_timeframe"],
                "evidence_mode": r["evidence_mode"],
                "relevance": r["relevance"],
                "direction": r["direction"],
                "assigned_at": r["assigned_at"],
            }
            for r in rows
        ]

    def get_primary_dimension_map(self, proposition_ids: list[str]) -> dict[str, str]:
        """For each proposition, return its highest-relevance dimension name.

        Returns {proposition_id: dimension_name} using the top-scoring
        model_evidence assignment per proposition.
        """
        if not proposition_ids:
            return {}
        placeholders = ",".join("?" * len(proposition_ids))
        rows = self._conn.execute(
            f"""SELECT me.proposition_id, um.dimension, me.relevance
                FROM model_evidence me
                JOIN user_model um ON me.model_id = um.id
                WHERE me.proposition_id IN ({placeholders})
                ORDER BY me.relevance DESC""",
            proposition_ids,
        ).fetchall()
        # First occurrence per prop_id wins (ordered by relevance DESC)
        result: dict[str, str] = {}
        for r in rows:
            if r["proposition_id"] not in result:
                result[r["proposition_id"]] = r["dimension"]
        return result

    def get_unassigned_propositions(self) -> list[dict]:
        """Get propositions with zero entries in model_evidence."""
        rows = self._conn.execute(
            """SELECT p.id, p.text, p.node_type, p.confidence, p.created_at,
                      p.event_timeframe, p.evidence_mode
               FROM propositions p
               LEFT JOIN model_evidence me ON p.id = me.proposition_id
               WHERE me.proposition_id IS NULL
               ORDER BY p.created_at""",
        ).fetchall()
        return [
            {
                "id": r["id"],
                "text": r["text"],
                "node_type": r["node_type"],
                "confidence": r["confidence"],
                "created_at": r["created_at"],
                "event_timeframe": r["event_timeframe"],
                "evidence_mode": r["evidence_mode"],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        self._conn.close()
