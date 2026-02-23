"""
Tests for UserModelStorage — Piece 1 of Build 4.

Covers: table creation, seeding, CRUD, evidence junction, lifecycle, migrations.
All tests use temp databases — no side effects on real data.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.user_model.storage import (
    UserModelStorage,
    EvidenceRow,
)

FIXTURES_DIR = Path(__file__).parent.parent / "data"
SEEDS_PATH = FIXTURES_DIR / "dimension_seeds.json"


@pytest.fixture
def storage(tmp_path):
    """Fresh UserModelStorage with propositions table pre-created."""
    db_path = tmp_path / "test.db"
    import sqlite3
    # Pre-create propositions + embeddings tables (simulates consolidated DB)
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE propositions (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            node_type TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            event_timeframe TEXT,
            evidence_mode TEXT DEFAULT 'experiential',
            status TEXT DEFAULT 'active'
        );
        CREATE TABLE embeddings (
            proposition_id TEXT PRIMARY KEY,
            embedding BLOB NOT NULL,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL
        );
    """)
    conn.commit()
    conn.close()

    store = UserModelStorage(db_path)
    yield store
    store.close()


@pytest.fixture
def seeded_storage(storage):
    """Storage with 4 seed dimensions loaded."""
    storage.seed_dimensions(SEEDS_PATH)
    return storage


def _insert_proposition(storage, prop_id: str, text: str, node_type: str = "stance"):
    """Helper: insert a proposition directly into the test DB."""
    now = datetime.now(timezone.utc).isoformat()
    storage._conn.execute(
        "INSERT INTO propositions (id, text, node_type, confidence, created_at) VALUES (?, ?, ?, ?, ?)",
        (prop_id, text, node_type, 0.8, now),
    )
    storage._conn.commit()


# ------------------------------------------------------------------
# Table creation
# ------------------------------------------------------------------

class TestTableCreation:
    def test_user_model_table_exists(self, storage):
        tables = {r[0] for r in storage._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "user_model" in tables

    def test_model_evidence_table_exists(self, storage):
        tables = {r[0] for r in storage._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "model_evidence" in tables

    def test_empty_on_creation(self, storage):
        dims = storage.get_all_dimensions()
        assert dims == []


# ------------------------------------------------------------------
# Seeding
# ------------------------------------------------------------------

class TestSeeding:
    def test_seeds_four_dimensions(self, seeded_storage):
        dims = seeded_storage.get_all_dimensions()
        assert len(dims) == 4

    def test_seed_ids(self, seeded_storage):
        ids = {d.id for d in seeded_storage.get_all_dimensions()}
        assert ids == {"self", "pursuits", "relationships", "body"}

    def test_seed_initial_state(self, seeded_storage):
        d = seeded_storage.get_dimension("self")
        assert d is not None
        assert d.confidence == 0.0
        assert d.uncertainty_type == "sparse"
        assert d.estimate == ""
        assert d.evidence_count == 0
        assert d.status == "active"
        assert d.parent_id is None

    def test_seed_decay_classes(self, seeded_storage):
        dims = {d.id: d.decay_class for d in seeded_storage.get_all_dimensions()}
        assert dims["self"] == "core"
        assert dims["pursuits"] == "preference"
        assert dims["relationships"] == "preference"
        assert dims["body"] == "situational"

    def test_seeding_is_idempotent(self, seeded_storage):
        seeded_storage.seed_dimensions(SEEDS_PATH)
        seeded_storage.seed_dimensions(SEEDS_PATH)
        assert len(seeded_storage.get_all_dimensions()) == 4


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------

class TestCRUD:
    def test_update_dimension(self, seeded_storage):
        seeded_storage.update_dimension(
            "self",
            estimate="Strong self-regulation patterns observed",
            confidence=0.6,
            uncertainty_type="stable",
            reasoning_trace="Based on morning formula + afternoon murk evidence",
            evidence_count=15,
        )
        d = seeded_storage.get_dimension("self")
        assert d.estimate == "Strong self-regulation patterns observed"
        assert d.confidence == 0.6
        assert d.uncertainty_type == "stable"
        assert d.evidence_count == 15
        assert "morning formula" in d.reasoning_trace

    def test_append_history(self, seeded_storage):
        seeded_storage.append_history("self", "Old estimate", 0.3, "2026-02-01T00:00:00")
        d = seeded_storage.get_dimension("self")
        assert len(d.summary_history) == 1
        assert d.summary_history[0]["estimate"] == "Old estimate"
        assert d.summary_history[0]["confidence"] == 0.3

    def test_append_history_accumulates(self, seeded_storage):
        seeded_storage.append_history("self", "First", 0.2, "2026-01-01T00:00:00")
        seeded_storage.append_history("self", "Second", 0.4, "2026-02-01T00:00:00")
        d = seeded_storage.get_dimension("self")
        assert len(d.summary_history) == 2
        assert d.summary_history[0]["estimate"] == "First"
        assert d.summary_history[1]["estimate"] == "Second"

    def test_get_nonexistent_dimension(self, seeded_storage):
        assert seeded_storage.get_dimension("nonexistent") is None

    def test_get_children_empty(self, seeded_storage):
        children = seeded_storage.get_children("self")
        assert children == []


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------

class TestLifecycle:
    def test_propose_dimension(self, seeded_storage):
        seeded_storage.propose_dimension(
            dim_id="self.regulation",
            dimension="self",
            subdimension="regulation",
            description="Daily coping, energy management, routine structures",
            proposed_from="cluster_detection",
            parent_id="self",
        )
        d = seeded_storage.get_dimension("self.regulation")
        assert d is not None
        assert d.status == "proposed"
        assert d.parent_id == "self"
        assert d.proposed_from == "cluster_detection"

    def test_proposed_not_in_active_list(self, seeded_storage):
        seeded_storage.propose_dimension(
            "self.regulation", "self", "regulation",
            "test", "cluster_detection", "self",
        )
        active = seeded_storage.get_all_dimensions(status="active")
        proposed = seeded_storage.get_all_dimensions(status="proposed")
        assert len(active) == 4
        assert len(proposed) == 1

    def test_confirm_dimension(self, seeded_storage):
        seeded_storage.propose_dimension(
            "self.regulation", "self", "regulation",
            "test", "cluster_detection", "self",
        )
        seeded_storage.confirm_dimension("self.regulation")
        d = seeded_storage.get_dimension("self.regulation")
        assert d.status == "active"
        assert d.proposed_from is None

    def test_confirm_shows_as_child(self, seeded_storage):
        seeded_storage.propose_dimension(
            "self.regulation", "self", "regulation",
            "test", "cluster_detection", "self",
        )
        seeded_storage.confirm_dimension("self.regulation")
        children = seeded_storage.get_children("self")
        assert len(children) == 1
        assert children[0].id == "self.regulation"

    def test_retire_dimension(self, seeded_storage):
        seeded_storage.retire_dimension("body")
        d = seeded_storage.get_dimension("body")
        assert d.status == "retired"
        active = seeded_storage.get_all_dimensions()
        assert len(active) == 3

    def test_rename_dimension(self, seeded_storage):
        seeded_storage.rename_dimension("self", "Updated description of internal world")
        d = seeded_storage.get_dimension("self")
        assert d.description == "Updated description of internal world"

    def test_propose_is_idempotent(self, seeded_storage):
        seeded_storage.propose_dimension(
            "self.regulation", "self", "regulation",
            "test", "cluster_detection", "self",
        )
        seeded_storage.propose_dimension(
            "self.regulation", "self", "regulation",
            "different", "user_request", "self",
        )
        d = seeded_storage.get_dimension("self.regulation")
        assert d.description == "test"  # first one wins


# ------------------------------------------------------------------
# Evidence junction
# ------------------------------------------------------------------

class TestEvidence:
    def test_store_and_retrieve_assignments(self, seeded_storage):
        _insert_proposition(seeded_storage, "p1", "I value deep focus work")
        _insert_proposition(seeded_storage, "p2", "Morning formula is load-bearing")
        now = datetime.now(timezone.utc).isoformat()

        seeded_storage.store_assignments([
            EvidenceRow("self", "p1", 0.8, "supports", now, "exhale"),
            EvidenceRow("self", "p2", 0.9, "supports", now, "exhale"),
        ])

        evidence = seeded_storage.get_evidence_for_dimension("self")
        assert len(evidence) == 2
        texts = {e["text"] for e in evidence}
        assert "I value deep focus work" in texts
        assert "Morning formula is load-bearing" in texts

    def test_evidence_count_updates(self, seeded_storage):
        _insert_proposition(seeded_storage, "p1", "test prop")
        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("pursuits", "p1", 0.7, "supports", now, "exhale"),
        ])
        d = seeded_storage.get_dimension("pursuits")
        assert d.evidence_count == 1
        assert d.last_evidence_at is not None

    def test_multi_dimension_assignment(self, seeded_storage):
        _insert_proposition(seeded_storage, "p1", "Career anxiety from childhood instability")
        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("self", "p1", 0.9, "supports", now, "exhale"),
            EvidenceRow("pursuits", "p1", 0.6, "contextualizes", now, "exhale"),
        ])
        self_ev = seeded_storage.get_evidence_for_dimension("self")
        pursuits_ev = seeded_storage.get_evidence_for_dimension("pursuits")
        assert len(self_ev) == 1
        assert len(pursuits_ev) == 1
        assert pursuits_ev[0]["direction"] == "contextualizes"

    def test_duplicate_assignment_ignored(self, seeded_storage):
        _insert_proposition(seeded_storage, "p1", "test")
        now = datetime.now(timezone.utc).isoformat()
        assignment = EvidenceRow("self", "p1", 0.8, "supports", now, "exhale")
        seeded_storage.store_assignments([assignment])
        seeded_storage.store_assignments([assignment])  # duplicate
        assert len(seeded_storage.get_evidence_for_dimension("self")) == 1

    def test_unassigned_propositions(self, seeded_storage):
        _insert_proposition(seeded_storage, "p1", "assigned")
        _insert_proposition(seeded_storage, "p2", "unassigned")
        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("self", "p1", 0.8, "supports", now, "exhale"),
        ])
        unassigned = seeded_storage.get_unassigned_propositions()
        assert len(unassigned) == 1
        assert unassigned[0]["id"] == "p2"

    def test_empty_evidence_for_dimension(self, seeded_storage):
        evidence = seeded_storage.get_evidence_for_dimension("self")
        assert evidence == []


# ------------------------------------------------------------------
# Migrations
# ------------------------------------------------------------------

class TestMigrations:
    def test_evidence_mode_column_added(self, storage):
        storage.add_evidence_mode_column()
        cols = {c["name"] for c in storage._conn.execute(
            "PRAGMA table_info(propositions)"
        ).fetchall()}
        assert "evidence_mode" in cols

    def test_evidence_mode_default_value(self, storage):
        storage.add_evidence_mode_column()
        _insert_proposition(storage, "p1", "test")
        row = storage._conn.execute(
            "SELECT evidence_mode FROM propositions WHERE id = 'p1'"
        ).fetchone()
        assert row["evidence_mode"] == "experiential"

    def test_evidence_mode_idempotent(self, storage):
        storage.add_evidence_mode_column()
        storage.add_evidence_mode_column()  # no error
        cols = [c["name"] for c in storage._conn.execute(
            "PRAGMA table_info(propositions)"
        ).fetchall()]
        assert cols.count("evidence_mode") == 1


    # Pass 2 storage methods

    def test_update_assignment(self, seeded_storage):
        _insert_proposition(seeded_storage, "p1", "test")
        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("self", "p1", 0.5, "supports", now, "assignment_p1"),
        ])
        seeded_storage.update_assignment("self", "p1", 0.85, "contextualizes")
        evidence = seeded_storage.get_evidence_for_dimension("self")
        assert evidence[0]["relevance"] == 0.85
        assert evidence[0]["direction"] == "contextualizes"

    def test_update_assignments_batch(self, seeded_storage):
        _insert_proposition(seeded_storage, "p1", "test1")
        _insert_proposition(seeded_storage, "p2", "test2")
        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("self", "p1", 0.5, "supports", now, "assignment_p1"),
            EvidenceRow("pursuits", "p2", 0.5, "supports", now, "assignment_p1"),
        ])
        seeded_storage.update_assignments_batch([
            ("self", "p1", 0.9, "supports"),
            ("pursuits", "p2", 0.3, "contextualizes"),
        ])
        ev_self = seeded_storage.get_evidence_for_dimension("self")
        ev_pursuits = seeded_storage.get_evidence_for_dimension("pursuits")
        assert ev_self[0]["relevance"] == 0.9
        assert ev_pursuits[0]["relevance"] == 0.3
        assert ev_pursuits[0]["direction"] == "contextualizes"

    def test_get_all_assignments(self, seeded_storage):
        _insert_proposition(seeded_storage, "p1", "test1")
        _insert_proposition(seeded_storage, "p2", "test2")
        now = datetime.now(timezone.utc).isoformat()
        seeded_storage.store_assignments([
            EvidenceRow("self", "p1", 0.5, "supports", now, "assignment_p1"),
            EvidenceRow("pursuits", "p2", 0.5, "supports", now, "assignment_p1"),
        ])
        all_a = seeded_storage.get_all_assignments()
        assert len(all_a) == 2
        assert all(a["text"] for a in all_a)  # joined with propositions
        assert all(a["model_id"] for a in all_a)
