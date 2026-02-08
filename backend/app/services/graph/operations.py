"""
Graph CRUD Operations for Voku v0.3

Handles all Kuzu graph operations:
- Node creation/update/retrieval (User Space + Organization Space)
- Edge creation/traversal
- Embedding storage and retrieval
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import kuzu
import numpy as np
from app.services.graph.constants import (
    ALL_NODE_TABLES,
    EDGE_CONSTRAINTS,
    RELATIONSHIP_EDGE_TYPES,
    VALID_EDGE_TYPES,
)

# Type aliases for clarity
NodePurpose = Literal["observation", "pattern", "belief", "intention", "decision"]
SourceType = Literal["explicit", "inferred"]
SignalValence = Literal["positive", "negative", "neutral"]
EdgeDirection = Literal["outgoing", "incoming"]


@dataclass
class GraphOperations:
    """Stateful wrapper around Kuzu database operations."""

    db: kuzu.Database

    def __post_init__(self):
        self._conn = kuzu.Connection(self.db)

    # ==========================================================================
    # Node Operations
    # ==========================================================================

    def create_module(
        self,
        title: str,
        content: str,
        intentions: dict,
        priority: int = 0,
        research_depth: int = 5,
    ) -> dict:
        """Create a ModuleNode (user-declared focus area).

        Args:
            title: Module title
            content: Description of the module
            intentions: Dict with keys: primary, secondary[], definition_of_done, declared_priority
            priority: Numeric ranking among modules
            research_depth: Default depth (0-10) for operations under this module

        Returns:
            Dict with all node fields including generated 'id'
        """
        node_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        self._conn.execute(
            """
            CREATE (n:ModuleNode {
                id: $id,
                title: $title,
                content: $content,
                intentions: $intentions,
                priority: $priority,
                research_depth: $research_depth,
                active: true,
                declared_at: $declared_at,
                created_at: $created_at,
                updated_at: $updated_at
            })
            """,
            {
                "id": node_id,
                "title": title,
                "content": content,
                "intentions": json.dumps(intentions),
                "priority": priority,
                "research_depth": research_depth,
                "declared_at": now,
                "created_at": now,
                "updated_at": now,
            },
        )

        return {
            "id": node_id,
            "title": title,
            "content": content,
            "intentions": intentions,
            "priority": priority,
            "research_depth": research_depth,
            "active": True,
            "declared_at": now,
            "created_at": now,
            "updated_at": now,
        }

    def create_internal_node(
        self,
        title: str,
        content: str,
        source: str,
        node_purpose: NodePurpose,
        source_type: SourceType,
        signal_valence: SignalValence | None = None,
        confidence: float = 1.0,
    ) -> dict:
        """Create an InternalNode (abstraction/cluster of beliefs).

        Args:
            title: Semantic slug (e.g., 'running-pattern-jan2024')
            content: Full text content of the abstraction
            source: Origin - 'conversation', 'voku', 'user', 'import'
            node_purpose: 'observation', 'pattern', 'belief', 'intention', 'decision'
            source_type: 'explicit' (user stated) or 'inferred' (Voku detected)
            signal_valence: 'positive', 'negative', 'neutral', or None
            confidence: 0.0-1.0 certainty score (default 1.0)

        Returns:
            Dict with all node fields including generated 'id'
        """
        return self._create_content_node(
            table="InternalNode",
            title=title,
            content=content,
            source=source,
            node_purpose=node_purpose,
            source_type=source_type,
            signal_valence=signal_valence,
            confidence=confidence,
        )

    def create_leaf_node(
        self,
        title: str,
        content: str,
        source: str,
        node_purpose: NodePurpose,
        source_type: SourceType,
        signal_valence: SignalValence | None = None,
        confidence: float = 1.0,
    ) -> dict:
        """Create a LeafNode (atomic belief/fact).

        Args:
            title: Semantic slug (e.g., '5k-run-session-2430-jan28')
            content: Full text content of the belief/fact
            source: Origin - 'conversation', 'voku', 'user', 'import'
            node_purpose: 'observation', 'pattern', 'belief', 'intention', 'decision'
            source_type: 'explicit' (user stated) or 'inferred' (Voku detected)
            signal_valence: 'positive', 'negative', 'neutral', or None
            confidence: 0.0-1.0 certainty score (default 1.0)

        Returns:
            Dict with all node fields including generated 'id'
        """
        return self._create_content_node(
            table="LeafNode",
            title=title,
            content=content,
            source=source,
            node_purpose=node_purpose,
            source_type=source_type,
            signal_valence=signal_valence,
            confidence=confidence,
        )

    def _create_content_node(
        self,
        table: str,
        title: str,
        content: str,
        source: str,
        node_purpose: str,
        source_type: str,
        signal_valence: str | None,
        confidence: float,
    ) -> dict:
        """Internal helper to create InternalNode or LeafNode (shared schema)."""
        node_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        self._conn.execute(
            f"""
            CREATE (n:{table} {{
                id: $id,
                title: $title,
                content: $content,
                source: $source,
                node_purpose: $node_purpose,
                source_type: $source_type,
                signal_valence: $signal_valence,
                confidence: $confidence,
                created_at: $created_at,
                updated_at: $updated_at
            }})
            """,
            {
                "id": node_id,
                "title": title,
                "content": content,
                "source": source,
                "node_purpose": node_purpose,
                "source_type": source_type,
                "signal_valence": signal_valence,
                "confidence": confidence,
                "created_at": now,
                "updated_at": now,
            },
        )

        return {
            "id": node_id,
            "title": title,
            "content": content,
            "source": source,
            "node_purpose": node_purpose,
            "source_type": source_type,
            "signal_valence": signal_valence,
            "confidence": confidence,
            "created_at": now,
            "updated_at": now,
        }

    def get_node(self, node_id: str) -> dict | None:
        """Retrieve any node by ID.

        Args:
            node_id: UUID of the node

        Returns:
            Node dict with parsed JSON fields, or None if not found
        """
        result = self._get_node_with_table(node_id)
        return result[0] if result else None

    def _get_node_with_table(self, node_id: str) -> tuple[dict, str] | None:
        """Retrieve any node by ID along with its table name.

        Returns:
            Tuple of (node dict, table name) or None if not found
        """
        for table in ALL_NODE_TABLES:
            query_result = self._conn.execute(
                f"MATCH (n:{table} {{id: $id}}) RETURN n",
                {"id": node_id},
            )
            records = query_result.get_all()

            if records:
                node = dict(records[0][0])
                self._parse_json_fields(node)
                return node, table

        return None

    def _parse_json_fields(self, node: dict) -> None:
        """Parse known JSON fields in-place."""
        if "intentions" in node and isinstance(node["intentions"], str):
            node["intentions"] = json.loads(node["intentions"])

    # ==========================================================================
    # Edge Operations
    # ==========================================================================

    def create_edge(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        confidence: float = 1.0,
        rationale: str | None = None,
    ) -> dict:
        """Create an edge between nodes.

        Args:
            from_id: Source node UUID
            to_id: Target node UUID
            rel_type: CONTAINS, SUPPORTS, CONTRADICTS, ENABLES, SUPERSEDES, REFERENCES
            confidence: Confidence score 0.0-1.0 (default 1.0)
            rationale: Text rationale (used by SUPPORTS/CONTRADICTS)

        Returns:
            Dict with edge details

        Raises:
            ValueError: Invalid rel_type or table combination
            LookupError: from_id or to_id not found
        """
        # Validate edge type
        if rel_type not in VALID_EDGE_TYPES:
            raise ValueError(
                f"Invalid edge type: {rel_type}. Must be one of {VALID_EDGE_TYPES}."
            )

        # Lookup nodes and their tables
        from_result = self._get_node_with_table(from_id)
        if not from_result:
            raise LookupError(f"Source node ID {from_id} not found.")
        _, from_table = from_result

        to_result = self._get_node_with_table(to_id)
        if not to_result:
            raise LookupError(f"Target node ID {to_id} not found.")
        _, to_table = to_result

        # Validate table combination
        if (from_table, to_table) not in EDGE_CONSTRAINTS[rel_type]:
            raise ValueError(
                f"{rel_type} edge cannot be created from {from_table} to {to_table}. "
                f"Valid: {EDGE_CONSTRAINTS[rel_type]}"
            )

        # Build query based on edge type properties
        created_at = datetime.now(timezone.utc)
        props, params = self._build_edge_props(
            rel_type, from_id, to_id, confidence, rationale, created_at
        )

        query = f"""
            MATCH (a:{from_table} {{id: $from_id}}), (b:{to_table} {{id: $to_id}})
            CREATE (a)-[r:{rel_type} {{{props}}}]->(b)
        """
        self._conn.execute(query, params)

        return {
            "from_id": from_id,
            "to_id": to_id,
            "rel_type": rel_type,
            "confidence": confidence,
            "rationale": rationale,
            "created_at": created_at,
        }

    def _build_edge_props(
        self,
        rel_type: str,
        from_id: str,
        to_id: str,
        confidence: float,
        rationale: str | None,
        created_at: datetime,
    ) -> tuple[str, dict]:
        """Build property string and params dict for edge creation."""
        base_params = {
            "from_id": from_id,
            "to_id": to_id,
            "created_at": created_at,
        }

        if rel_type in ("SUPPORTS", "CONTRADICTS"):
            props = "confidence: $confidence, rationale: $rationale, created_at: $created_at"
            return props, {
                **base_params,
                "confidence": confidence,
                "rationale": rationale,
            }

        if rel_type == "SUPERSEDES":
            props = "created_at: $created_at"
            return props, base_params

        # CONTAINS, ENABLES, REFERENCES
        props = "confidence: $confidence, created_at: $created_at"
        return props, {**base_params, "confidence": confidence}

    def get_children(self, node_id: str) -> list[dict]:
        """Get all nodes connected via CONTAINS from this node.

        Args:
            node_id: Parent node UUID

        Returns:
            List of child node dicts
        """
        parent_result = self._get_node_with_table(node_id)
        if not parent_result:
            return []

        _, parent_table = parent_result

        # Only ModuleNode and InternalNode can have CONTAINS children
        if parent_table not in ("ModuleNode", "InternalNode"):
            return []

        result = self._conn.execute(
            f"MATCH (p:{parent_table} {{id: $id}})-[:CONTAINS]->(c) RETURN c",
            {"id": node_id},
        )

        children = []
        for record in result.get_all():
            node = dict(record[0])
            self._parse_json_fields(node)
            children.append(node)

        return children

    def get_related(
        self,
        node_id: str,
        rel_type: str | None = None,
    ) -> list[dict]:
        """Get nodes related via SUPPORTS, CONTRADICTS, ENABLES, or SUPERSEDES.

        Unlike get_children() which only handles CONTAINS hierarchy, this method
        returns semantic relationships with direction information.

        Args:
            node_id: Node UUID to find relationships for
            rel_type: Filter to specific relationship type, or None for all

        Returns:
            List of dicts with 'node' and 'direction' ('outgoing' or 'incoming')
        """
        node_result = self._get_node_with_table(node_id)
        if not node_result:
            return []

        _, node_table = node_result

        # Determine which edge types to query
        if rel_type:
            if rel_type not in RELATIONSHIP_EDGE_TYPES:
                return []
            edge_types = [rel_type]
        else:
            edge_types = list(RELATIONSHIP_EDGE_TYPES)

        related: list[dict] = []

        for edge_type in edge_types:
            # Outgoing: this node -> other
            related.extend(
                self._query_related_direction(
                    node_id, node_table, edge_type, "outgoing"
                )
            )
            # Incoming: other -> this node
            related.extend(
                self._query_related_direction(
                    node_id, node_table, edge_type, "incoming"
                )
            )

        return related

    def _query_related_direction(
        self,
        node_id: str,
        node_table: str,
        edge_type: str,
        direction: EdgeDirection,
    ) -> list[dict]:
        """Query related nodes in a specific direction."""
        if direction == "outgoing":
            query = f"""
                MATCH (n:{node_table} {{id: $id}})-[:{edge_type}]->(related)
                RETURN related
            """
        else:
            query = f"""
                MATCH (n:{node_table} {{id: $id}})<-[:{edge_type}]-(related)
                RETURN related
            """

        result = self._conn.execute(query, {"id": node_id})
        records = result.get_all()

        related = []
        for record in records:
            node = dict(record[0])
            self._parse_json_fields(node)
            related.append({"node": node, "direction": direction})

        return related

    # ==========================================================================
    # Embedding Operations (TODO)
    # ==========================================================================

    def store_embedding(
        self,
        node_id: str,
        embedding_type: str,
        embedding: list[float],
        model: str,
    ) -> None:
        """Store an embedding for a node.

        Args:
            node_id: Node UUID
            embedding_type: 'content', 'title', 'context', or 'query'
            embedding: 768-dimensional vector
            model: Model name used for generation
        """
        embedding_id = str(uuid.uuid4())

        query = """
            CREATE (e:NodeEmbedding {
                id: $id,
                node_id: $node_id,
                embedding_type: $embedding_type,
                embedding: $embedding,
                model: $model,
                created_at: $created_at
            })
        """

        self._conn.execute(
            query,
            {
                "id": embedding_id,
                "node_id": node_id,
                "embedding_type": embedding_type,
                "embedding": embedding,
                "model": model,
                "created_at": datetime.now(timezone.utc),
            },
        )

    def get_embeddings(self, node_id: str) -> dict[str, list[float]]:
        """Get all embeddings for a node, keyed by embedding_type.

        Args:
            node_id: Node UUID to get embeddings for

        Returns:
            Dict mapping embedding_type to embedding vector
            eg. {
                "content": [...],
                "title": [...],
                "context": [...],
            }
        """
        query = """
            MATCH (e:NodeEmbedding {node_id: $node_id})
            RETURN e.embedding_type, e.embedding
        """

        result = self._conn.execute(query, {"node_id": node_id})
        records = result.get_all()

        embeddings = {}
        for record in records:
            embedding_type, embedding = record
            embeddings[embedding_type] = embedding

        return embeddings

    def find_similar_nodes(
        self,
        embedding: list[float],
        embedding_type: str = "content",
        threshold: float = 0.95,
        limit: int = 10,
    ) -> list[dict]:
        """
        Find nodes with cosine similarity above threshold for a given embedding.

        Future: use Kuzu's HNSW vector index for O(log n) similarity search instead of brute-force.

        Args:
            embedding: Query vectory (768-dim)
            embedding_type: Type of embedding to compare ('content', 'title', etc.)
            threshold: Minimum cosine similarity to consider a match (0.0-1.0; default 0.95)
            limit: Maximum number of similar nodes to return

        Returns:
            List of dicts with keys: 'node_id', 'similarity', and 'embedding'
            Sorted by similarity descending, limited to 'limit' results
        """
        # Query all embeddings of the specified type
        query = """
            MATCH (e:NodeEmbedding {embedding_type: $embedding_type})
            RETURN e.node_id, e.embedding
        """

        result = self._conn.execute(query, {"embedding_type": embedding_type})
        records = result.get_all()

        if not records:
            return []

        # Convert query embedding to numpy array for similarity calculation

        query_vec = np.array(embedding)
        query_norm = np.linalg.norm(query_vec)

        similar_nodes = []

        for record in records:
            node_id, node_embedding = record
            node_vec = np.array(node_embedding)
            node_norm = np.linalg.norm(node_vec)

            if query_norm == 0 or node_norm == 0:
                continue  # Avoid division by zero

            cosine_similarity = np.dot(query_vec, node_vec) / (query_norm * node_norm)

            if cosine_similarity >= threshold:
                similar_nodes.append(
                    {
                        "node_id": node_id,
                        "similarity": cosine_similarity,
                        "embedding": node_embedding,
                    }
                )

        # Sort by similarity descending and limit results
        similar_nodes.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_nodes[:limit]

    # ==========================================================================
    # Query Operations (TODO)
    # ==========================================================================

    def get_module_tree(self, root_id: str, max_depth: int = 3) -> dict:
        """Get hierarchical tree under a module."""
        raise NotImplementedError()

    def find_contradictions(self, node_id: str) -> list[dict]:
        """Find nodes that contradict this node."""
        raise NotImplementedError()
