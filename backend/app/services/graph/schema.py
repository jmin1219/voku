"""
Kuzu Graph Schema for Voku v0.3

Phase A implementation:
- User Space: ModuleNode, InternalNode, LeafNode
- Organization Space: OrganizationNode
- Edges: CONTAINS, SUPPORTS, CONTRADICTS, ENABLES, SUPERSEDES, REFERENCES
- NodeEmbedding table

See docs/DESIGN_V03.md Section 6 for complete schema specification.
"""

from pathlib import Path

import kuzu


def init_database(db_path: str | Path) -> kuzu.Database:
    """Initialize Kuzu database with Voku schema.

    Args:
        db_path: Path to database directory (created if doesn't exist)

    Returns:
        Initialized kuzu.Database instance
    """
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    _create_node_tables(conn)
    _create_edge_tables(conn)
    _create_embedding_table(conn)

    return db

def _create_node_tables(conn: kuzu.Connection) -> None:
    """Create User Space and Organization Space node tables."""

    # ModuleNode: User-declared focus areas (modules)
    # - intentions: JSON {primary, secondary[], definition_of_done, declared_priority}
    # - priority: numeric ranking among modules
    # - research_depth: default depth (0-10) for operations under this module
    # - active: whether module is currently in use
    # - declared_at: when user created this module (may differ from created_at for imports)
    conn.execute("""
        CREATE NODE TABLE ModuleNode (
            id STRING,
            title STRING,
            content STRING,
            intentions STRING,
            priority INT64,
            research_depth INT64 DEFAULT 5,
            active BOOLEAN DEFAULT true,
            declared_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (id)
        )
    """)

    # InternalNode: Confirmed abstractions (clusters of beliefs)
    # - status: confirmed | suggested | faded | rejected (ghost lifecycle)
    # - source: conversation | voku | user | import
    # - confidence: 0.0-1.0 certainty score
    # - node_purpose: observation | pattern | belief | intention | decision
    # - source_type: explicit (user stated) | inferred (Voku detected)
    # - signal_valence: positive | negative | neutral (relative to module intention)
    # - valid_from/valid_to: bi-temporal (when you believed this)
    # - recorded_at: bi-temporal (when Voku learned it)
    # - suggested_at: when Voku proposed this ghost node
    conn.execute("""
        CREATE NODE TABLE InternalNode (
            id STRING,
            title STRING,
            content STRING,
            status STRING DEFAULT 'confirmed',
            source STRING,
            confidence FLOAT DEFAULT 1.0,
            node_purpose STRING,
            source_type STRING,
            signal_valence STRING,
            valid_from TIMESTAMP,
            valid_to TIMESTAMP,
            recorded_at TIMESTAMP,
            suggested_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (id)
        )
    """)

    # LeafNode: Atomic beliefs/facts extracted from conversation
    # Same fields as InternalNode but represents raw extractions, not abstractions
    conn.execute("""
        CREATE NODE TABLE LeafNode (
            id STRING,
            title STRING,
            content STRING,
            status STRING DEFAULT 'confirmed',
            source STRING,
            confidence FLOAT DEFAULT 1.0,
            node_purpose STRING,
            source_type STRING,
            signal_valence STRING,
            valid_from TIMESTAMP,
            valid_to TIMESTAMP,
            recorded_at TIMESTAMP,
            suggested_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (id)
        )
    """)

    # OrganizationNode: Voku's hidden cognitive workspace
    # - type: compression | priority | pattern | hypothesis | keyword | bridge
    # User can inspect ("why did you suggest this?") but doesn't clutter their graph
    conn.execute("""
        CREATE NODE TABLE OrganizationNode (
            id STRING,
            type STRING,
            title STRING,
            content STRING,
            confidence FLOAT,
            valid_from TIMESTAMP,
            valid_to TIMESTAMP,
            created_at TIMESTAMP,
            PRIMARY KEY (id)
        )
    """)


def _create_edge_tables(conn: kuzu.Connection) -> None:
    """Create relationship tables using data-driven schema definition.
    
    Kuzu uses REL TABLE GROUP for relationships spanning multiple node types.
    Each (from, to) pair is listed separately.
    """

    # Edge schema definitions
    # from_to_pairs: list of (from_node, to_node) tuples
    # properties: (name, type, default) where default=None means no default
    EDGE_SCHEMAS = [
        # User Space hierarchy
        {
            "name": "CONTAINS",
            "from_to_pairs": [
                ("ModuleNode", "InternalNode"),
                ("ModuleNode", "LeafNode"),
                ("InternalNode", "InternalNode"),
                ("InternalNode", "LeafNode"),
            ],
            "properties": [
                ("status", "STRING", "'confirmed'"),
                ("confidence", "FLOAT", "1.0"),
                ("created_at", "TIMESTAMP", None),
            ],
        },
        # Evidence/support relationship
        {
            "name": "SUPPORTS",
            "from_to_pairs": [
                ("LeafNode", "LeafNode"),
                ("LeafNode", "InternalNode"),
                ("InternalNode", "LeafNode"),
                ("InternalNode", "InternalNode"),
            ],
            "properties": [
                ("status", "STRING", "'confirmed'"),
                ("confidence", "FLOAT", "1.0"),
                ("rationale", "STRING", None),
                ("created_at", "TIMESTAMP", None),
            ],
        },
        # Conflicting beliefs
        {
            "name": "CONTRADICTS",
            "from_to_pairs": [
                ("LeafNode", "LeafNode"),
                ("LeafNode", "InternalNode"),
                ("InternalNode", "LeafNode"),
                ("InternalNode", "InternalNode"),
            ],
            "properties": [
                ("status", "STRING", "'confirmed'"),
                ("confidence", "FLOAT", "1.0"),
                ("rationale", "STRING", None),
                ("created_at", "TIMESTAMP", None),
            ],
        },
        # Prerequisite relationship
        {
            "name": "ENABLES",
            "from_to_pairs": [
                ("LeafNode", "LeafNode"),
                ("LeafNode", "InternalNode"),
                ("InternalNode", "LeafNode"),
                ("InternalNode", "InternalNode"),
            ],
            "properties": [
                ("status", "STRING", "'confirmed'"),
                ("confidence", "FLOAT", "1.0"),
                ("created_at", "TIMESTAMP", None),
            ],
        },
        # Belief evolution (new replaces old)
        {
            "name": "SUPERSEDES",
            "from_to_pairs": [
                ("LeafNode", "LeafNode"),
                ("LeafNode", "InternalNode"),
                ("InternalNode", "LeafNode"),
                ("InternalNode", "InternalNode"),
            ],
            "properties": [
                ("created_at", "TIMESTAMP", None),
            ],
        },
        # Organization space links to user space
        {
            "name": "REFERENCES",
            "from_to_pairs": [
                ("OrganizationNode", "ModuleNode"),
                ("OrganizationNode", "InternalNode"),
                ("OrganizationNode", "LeafNode"),
            ],
            "properties": [
                ("created_at", "TIMESTAMP", None),
            ],
        },
    ]

    for edge in EDGE_SCHEMAS:
        # Build FROM/TO pairs clause
        pairs_clause = ", ".join(
            f"FROM {f} TO {t}" for f, t in edge["from_to_pairs"]
        )

        # Build properties clause
        prop_parts = []
        for name, typ, default in edge["properties"]:
            if default:
                prop_parts.append(f"{name} {typ} DEFAULT {default}")
            else:
                prop_parts.append(f"{name} {typ}")
        props_clause = ", ".join(prop_parts)

        cypher = f"CREATE REL TABLE GROUP {edge['name']} ({pairs_clause}, {props_clause})"
        conn.execute(cypher)


def _create_embedding_table(conn: kuzu.Connection) -> None:
    """Create NodeEmbedding table for multi-aspect embeddings.
    
    Each node can have multiple embeddings:
    - content: literal meaning of text
    - title: semantic boundary  
    - context: node + parent summaries
    - query: hypothetical questions this node answers
    """
    conn.execute("""
        CREATE NODE TABLE NodeEmbedding (
            id STRING,
            node_id STRING,
            embedding_type STRING,
            embedding FLOAT[768],
            model STRING,
            created_at TIMESTAMP,
            PRIMARY KEY (id)
        )
    """)
