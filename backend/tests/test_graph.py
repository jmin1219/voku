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


class TestSchemaCreation:
    """Test that schema is created correctly."""

    def test_init_creates_database(self, temp_db):
        """Database should be created at specified path."""
        assert temp_db is not None


class TestNodeOperations:
    """Test node CRUD operations."""

    def test_create_module(self, graph_ops):
        """Should create a module (ModuleNode)."""
        # ARRANGE
        title = "Cardio Training"
        content = "Focus on improving cardiovascular health."
        intentions = {
            "primary": "Improve endurance",
            "secondary": ["Increase VO2 max"],
            "definition_of_done": "Run 5k under 25 minutes",
            "declared_priority": 1,
        }
        priority = 1
        research_depth = 7
        # ACT
        result = graph_ops.create_module(
            title=title,
            content=content,
            intentions=intentions,
            priority=priority,
            research_depth=research_depth,
        )
        # ASSERT
        assert result is not None
        assert "id" in result  # UUID generated
        assert result["title"] == title
        assert result["content"] == content
        assert result["intentions"] == intentions
        assert result["priority"] == priority
        assert result["research_depth"] == research_depth

    def test_create_leaf_node(self, graph_ops):
        """Should create an atomic belief (LeafNode)."""
        # ARRANGE
        title = "5k-run-session-2439-jan28"
        content = "Completed a 5 kilometer run in 25 minutes."
        source = "conversation"
        node_purpose = "observation"
        source_type = "explicit"
        # ACT
        result = graph_ops.create_leaf_node(
            title=title,
            content=content,
            source=source,
            node_purpose=node_purpose,
            source_type=source_type,
        )
        # ASSERT
        assert result is not None
        assert "id" in result  # UUID generated
        assert result["title"] == title
        assert result["content"] == content
        assert result["source"] == source
        assert result["node_purpose"] == node_purpose
        assert result["source_type"] == source_type

    def test_get_node_returns_none_for_missing(self, graph_ops):
        """get_node should return None for non-existent ID."""
        missing_id = "non-existent-id"
        result = graph_ops.get_node(missing_id)
        assert result is None

    def test_get_node_returns_created_node(self, graph_ops):
        """get_node should return a node that was created."""
        # ARRANGE
        title = "test-leaf-node"
        content = "This is a test leaf node."
        source = "user"
        node_purpose = "belief"
        source_type = "explicit"
        created = graph_ops.create_leaf_node(
            title=title,
            content=content,
            source=source,
            node_purpose=node_purpose,
            source_type=source_type,
        )
        node_id = created["id"]
        # ACT
        fetched = graph_ops.get_node(node_id)
        # ASSERT
        assert fetched is not None
        assert fetched["id"] == node_id
        assert fetched["title"] == title
        assert fetched["content"] == content

    def test_node_purpose_validation(self, graph_ops):
        """node_purpose should be one of: observation, pattern, belief, intention, decision."""
        # TODO: Implement
        pytest.skip("Implement after operations")

    def test_get_module_returns_created_module(self, graph_ops):
        """get_node should return a ModuleNode that was created."""
        # ARRANGE
        title = "Test Module"
        content = "Module content."
        intentions = {
            "primary": "Test primary intention",
            "secondary": [],
            "definition_of_done": "Test definition",
            "declared_priority": 2,
        }
        priority = 2
        research_depth = 5
        created = graph_ops.create_module(
            title=title,
            content=content,
            intentions=intentions,
            priority=priority,
            research_depth=research_depth,
        )
        module_id = created["id"]
        # ACT
        fetched = graph_ops.get_node(module_id)
        # ASSERT
        assert fetched is not None
        assert fetched["id"] == module_id
        assert fetched["title"] == title
        assert fetched["content"] == content
        assert fetched["intentions"] == intentions


class TestEdgeOperations:
    """Test edge creation and traversal."""

    def test_create_contains_edge(self, graph_ops):
        """Should link module to child node."""
        # TODO: Implement
        pytest.skip("Implement after operations")

    def test_get_children(self, graph_ops):
        """Should return all CONTAINS children."""
        # TODO: Implement
        pytest.skip("Implement after operations")

    def test_create_supports_edge(self, graph_ops):
        """Should link supporting nodes."""
        # TODO: Implement
        pytest.skip("Implement after operations")


class TestEmbeddingStorage:
    """Test embedding storage and retrieval."""

    def test_store_and_retrieve_embedding(self, graph_ops):
        """Should store and retrieve embeddings by type."""
        # TODO: Implement
        pytest.skip("Implement after operations")

    def test_multiple_embedding_types(self, graph_ops):
        """Should store content, title, context, query embeddings separately."""
        # TODO: Implement
        pytest.skip("Implement after operations")


class TestGraphIntegrity:
    """Test graph-level invariants."""

    def test_no_orphan_leaves(self, graph_ops):
        """Every LeafNode should have at least one parent."""
        # TODO: Implement
        pytest.skip("Implement after operations")

    def test_modules_are_roots(self, graph_ops):
        """ModuleNodes should have no incoming CONTAINS edges."""
        # TODO: Implement
        pytest.skip("Implement after operations")
