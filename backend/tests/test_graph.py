"""
Tests for Kuzu Graph Layer - Phase A

Test strategy:
1. Schema creation (tables exist, correct columns)
2. Node CRUD (create, read, update for each node type)
3. Edge CRUD (create edges, verify relationships)
4. Graph integrity (no orphan nodes, valid references)
5. Embedding storage/retrieval
"""

import tempfile
from pathlib import Path

import pytest

from app.services.graph.operations import GraphOperations
from app.services.graph.schema import init_database


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db():
    """Create a temporary Kuzu database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_voku.kuzu"
        db = init_database(db_path)
        yield db


@pytest.fixture
def graph_ops(temp_db):
    """GraphOperations instance with fresh database."""
    return GraphOperations(db=temp_db)


# =============================================================================
# Schema Tests
# =============================================================================


class TestSchemaCreation:
    """Test that schema is created correctly."""

    def test_init_creates_database(self, temp_db):
        """Database should be created at specified path."""
        assert temp_db is not None


# =============================================================================
# Node Operation Tests
# =============================================================================


class TestNodeOperations:
    """Test node CRUD operations."""

    # --- ModuleNode ---

    def test_create_module(self, graph_ops):
        """Should create a module (ModuleNode)."""
        result = graph_ops.create_module(
            title="Cardio Training",
            content="Focus on improving cardiovascular health.",
            intentions={
                "primary": "Improve endurance",
                "secondary": ["Increase VO2 max"],
                "definition_of_done": "Run 5k under 25 minutes",
                "declared_priority": 1,
            },
            priority=1,
            research_depth=7,
        )

        assert result is not None
        assert "id" in result
        assert result["title"] == "Cardio Training"
        assert result["intentions"]["primary"] == "Improve endurance"
        assert result["priority"] == 1
        assert result["research_depth"] == 7

    def test_get_module_returns_created_module(self, graph_ops):
        """get_node should return a ModuleNode that was created."""
        intentions = {
            "primary": "Test primary intention",
            "secondary": [],
            "definition_of_done": "Test definition",
            "declared_priority": 2,
        }
        created = graph_ops.create_module(
            title="Test Module",
            content="Module content.",
            intentions=intentions,
            priority=2,
            research_depth=5,
        )

        fetched = graph_ops.get_node(created["id"])

        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["title"] == "Test Module"
        assert fetched["intentions"] == intentions

    # --- InternalNode ---

    def test_create_internal_node(self, graph_ops):
        """Should create an abstraction (InternalNode)."""
        result = graph_ops.create_internal_node(
            title="running-pattern-negative-splits",
            content="Negative splits correlate with better finish times",
            source="voku",
            node_purpose="pattern",
            source_type="inferred",
        )

        assert result is not None
        assert "id" in result
        assert result["title"] == "running-pattern-negative-splits"
        assert result["source"] == "voku"
        assert result["node_purpose"] == "pattern"
        assert result["source_type"] == "inferred"

    def test_get_internal_node_returns_created(self, graph_ops):
        """get_node should return an InternalNode that was created."""
        created = graph_ops.create_internal_node(
            title="test-internal",
            content="Test abstraction",
            source="voku",
            node_purpose="pattern",
            source_type="inferred",
        )

        fetched = graph_ops.get_node(created["id"])

        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["title"] == "test-internal"

    # --- LeafNode ---

    def test_create_leaf_node(self, graph_ops):
        """Should create an atomic belief (LeafNode)."""
        result = graph_ops.create_leaf_node(
            title="5k-run-session-2439-jan28",
            content="Completed a 5 kilometer run in 25 minutes.",
            source="conversation",
            node_purpose="observation",
            source_type="explicit",
        )

        assert result is not None
        assert "id" in result
        assert result["title"] == "5k-run-session-2439-jan28"
        assert result["source"] == "conversation"
        assert result["node_purpose"] == "observation"
        assert result["source_type"] == "explicit"

    def test_get_node_returns_created_node(self, graph_ops):
        """get_node should return a LeafNode that was created."""
        created = graph_ops.create_leaf_node(
            title="test-leaf-node",
            content="This is a test leaf node.",
            source="user",
            node_purpose="belief",
            source_type="explicit",
        )

        fetched = graph_ops.get_node(created["id"])

        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["title"] == "test-leaf-node"
        assert fetched["content"] == "This is a test leaf node."

    # --- Edge cases ---

    def test_get_node_returns_none_for_missing(self, graph_ops):
        """get_node should return None for non-existent ID."""
        result = graph_ops.get_node("non-existent-id")
        assert result is None

    def test_node_purpose_validation(self, graph_ops):
        """node_purpose should be one of: observation, pattern, belief, intention, decision."""
        pytest.skip("Implement validation after core operations")


# =============================================================================
# Edge Operation Tests
# =============================================================================


class TestEdgeOperations:
    """Test edge creation and traversal."""

    # --- CONTAINS edges ---

    def test_create_contains_edge_module_to_leaf(self, graph_ops):
        """Should create CONTAINS edge from module to leaf."""
        module = graph_ops.create_module(
            title="Fitness",
            content="Physical training focus",
            intentions={
                "primary": "Get stronger",
                "secondary": [],
                "definition_of_done": "100kg squat",
                "declared_priority": "high",
            },
        )
        leaf = graph_ops.create_leaf_node(
            title="5k-run-jan28",
            content="Ran 5K in 24:30",
            source="conversation",
            node_purpose="observation",
            source_type="explicit",
        )

        edge = graph_ops.create_edge(
            from_id=module["id"],
            to_id=leaf["id"],
            rel_type="CONTAINS",
            confidence=1.0,
        )

        assert edge["from_id"] == module["id"]
        assert edge["to_id"] == leaf["id"]
        assert edge["rel_type"] == "CONTAINS"
        assert edge["confidence"] == 1.0

    def test_get_children_returns_contains_children(self, graph_ops):
        """Should return all CONTAINS children of a node."""
        module = graph_ops.create_module(
            title="Test Module",
            content="Test content",
            intentions={
                "primary": "Test",
                "secondary": [],
                "definition_of_done": "Done",
                "declared_priority": "high",
            },
        )
        leaf1 = graph_ops.create_leaf_node(
            title="leaf-1",
            content="Test content 1",
            source="user",
            node_purpose="observation",
            source_type="explicit",
        )
        leaf2 = graph_ops.create_leaf_node(
            title="leaf-2",
            content="Test content 2",
            source="user",
            node_purpose="observation",
            source_type="explicit",
        )

        graph_ops.create_edge(module["id"], leaf1["id"], "CONTAINS")
        graph_ops.create_edge(module["id"], leaf2["id"], "CONTAINS")

        children = graph_ops.get_children(module["id"])

        assert len(children) == 2
        assert {c["title"] for c in children} == {"leaf-1", "leaf-2"}

    def test_get_children_empty_for_leaf(self, graph_ops):
        """Leaf nodes cannot have CONTAINS children."""
        leaf = graph_ops.create_leaf_node(
            title="test-leaf",
            content="Test content",
            source="user",
            node_purpose="observation",
            source_type="explicit",
        )

        children = graph_ops.get_children(leaf["id"])

        assert children == []

    # --- SUPPORTS edges ---

    def test_create_supports_edge_with_rationale(self, graph_ops):
        """SUPPORTS edge should store rationale."""
        leaf1 = graph_ops.create_leaf_node(
            title="observation",
            content="I ran 5K in 24:30",
            source="conversation",
            node_purpose="observation",
            source_type="explicit",
        )
        leaf2 = graph_ops.create_leaf_node(
            title="pattern",
            content="Negative splits improve my finish times",
            source="conversation",
            node_purpose="pattern",
            source_type="inferred",
        )

        edge = graph_ops.create_edge(
            from_id=leaf1["id"],
            to_id=leaf2["id"],
            rel_type="SUPPORTS",
            confidence=0.8,
            rationale="This observation provides evidence for the pattern",
        )

        assert edge["rationale"] == "This observation provides evidence for the pattern"
        assert edge["confidence"] == 0.8

    # --- get_related ---

    def test_get_related_returns_outgoing_supports(self, graph_ops):
        """get_related should return nodes this node SUPPORTS (outgoing)."""
        leaf_a = graph_ops.create_leaf_node(
            title="observation-a",
            content="I ran 5K in 24:30",
            source="conversation",
            node_purpose="observation",
            source_type="explicit",
        )
        leaf_b = graph_ops.create_leaf_node(
            title="pattern-b",
            content="Negative splits improve finish times",
            source="voku",
            node_purpose="pattern",
            source_type="inferred",
        )
        graph_ops.create_edge(leaf_a["id"], leaf_b["id"], "SUPPORTS")

        related = graph_ops.get_related(leaf_a["id"], "SUPPORTS")

        assert len(related) == 1
        assert related[0]["node"]["id"] == leaf_b["id"]
        assert related[0]["direction"] == "outgoing"

    def test_get_related_returns_incoming_supports(self, graph_ops):
        """get_related should return nodes that SUPPORT this node (incoming)."""
        leaf_a = graph_ops.create_leaf_node(
            title="observation-a",
            content="I ran 5K in 24:30",
            source="conversation",
            node_purpose="observation",
            source_type="explicit",
        )
        leaf_b = graph_ops.create_leaf_node(
            title="pattern-b",
            content="Negative splits improve finish times",
            source="voku",
            node_purpose="pattern",
            source_type="inferred",
        )
        graph_ops.create_edge(leaf_a["id"], leaf_b["id"], "SUPPORTS")

        related = graph_ops.get_related(leaf_b["id"], "SUPPORTS")

        assert len(related) == 1
        assert related[0]["node"]["id"] == leaf_a["id"]
        assert related[0]["direction"] == "incoming"

    def test_get_related_empty_for_no_edges(self, graph_ops):
        """get_related should return empty list when no matching edges."""
        leaf = graph_ops.create_leaf_node(
            title="isolated",
            content="No connections",
            source="user",
            node_purpose="observation",
            source_type="explicit",
        )

        related = graph_ops.get_related(leaf["id"], "SUPPORTS")

        assert related == []

    # --- Error cases ---

    def test_create_edge_invalid_rel_type(self, graph_ops):
        """Should raise ValueError for invalid relationship type."""
        module = graph_ops.create_module(
            title="Test Module",
            content="Test content",
            intentions={
                "primary": "Test",
                "secondary": [],
                "definition_of_done": "Done",
                "declared_priority": "high",
            },
        )
        leaf = graph_ops.create_leaf_node(
            title="test-leaf",
            content="Test content",
            source="user",
            node_purpose="observation",
            source_type="explicit",
        )

        with pytest.raises(ValueError, match="Invalid edge type"):
            graph_ops.create_edge(module["id"], leaf["id"], "INVALID_TYPE")

    def test_create_edge_invalid_table_combination(self, graph_ops):
        """Should raise ValueError for invalid table combination."""
        leaf1 = graph_ops.create_leaf_node(
            title="leaf-1",
            content="Test content 1",
            source="user",
            node_purpose="observation",
            source_type="explicit",
        )
        leaf2 = graph_ops.create_leaf_node(
            title="leaf-2",
            content="Test content 2",
            source="user",
            node_purpose="observation",
            source_type="explicit",
        )

        with pytest.raises(ValueError, match="cannot be created"):
            graph_ops.create_edge(leaf1["id"], leaf2["id"], "CONTAINS")

    def test_create_edge_node_not_found(self, graph_ops):
        """Should raise LookupError for non-existent node."""
        module = graph_ops.create_module(
            title="Test Module",
            content="Test content",
            intentions={
                "primary": "Test",
                "secondary": [],
                "definition_of_done": "Done",
                "declared_priority": "high",
            },
        )

        with pytest.raises(LookupError, match="not found"):
            graph_ops.create_edge(module["id"], "fake-uuid", "CONTAINS")


# =============================================================================
# Embedding Tests (TODO)
# =============================================================================


class TestEmbeddingStorage:
    """Test embedding storage and retrieval."""

    def test_store_and_retrieve_embedding(self, graph_ops):
        """Should store and retrieve embeddings by type."""
        pytest.skip("Implement after core operations")

    def test_multiple_embedding_types(self, graph_ops):
        """Should store content, title, context, query embeddings separately."""
        pytest.skip("Implement after core operations")


# =============================================================================
# Graph Integrity Tests (TODO)
# =============================================================================


class TestGraphIntegrity:
    """Test graph-level invariants."""

    def test_no_orphan_leaves(self, graph_ops):
        """Every LeafNode should have at least one parent."""
        pytest.skip("Implement after core operations")

    def test_modules_are_roots(self, graph_ops):
        """ModuleNodes should have no incoming CONTAINS edges."""
        pytest.skip("Implement after core operations")
