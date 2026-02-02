"""
Graph Constants for Voku v0.3

Defines valid edge types, constraints, and table groupings.
"""

# All valid edge types in the system
VALID_EDGE_TYPES = {
    "CONTAINS",
    "SUPPORTS",
    "CONTRADICTS",
    "ENABLES",
    "SUPERSEDES",
    "REFERENCES",
}

# Semantic relationship edges (excludes CONTAINS hierarchy and REFERENCES)
# Used by get_related() for non-hierarchical traversal
RELATIONSHIP_EDGE_TYPES = {
    "SUPPORTS",
    "CONTRADICTS",
    "ENABLES",
    "SUPERSEDES",
}

# Maps edge type → set of valid (from_table, to_table) pairs
EDGE_CONSTRAINTS = {
    "CONTAINS": {
        ("ModuleNode", "InternalNode"),
        ("ModuleNode", "LeafNode"),
        ("InternalNode", "InternalNode"),
        ("InternalNode", "LeafNode"),
    },
    "SUPPORTS": {
        ("LeafNode", "LeafNode"),
        ("LeafNode", "InternalNode"),
        ("InternalNode", "LeafNode"),
        ("InternalNode", "InternalNode"),
    },
    "CONTRADICTS": {
        ("LeafNode", "LeafNode"),
        ("LeafNode", "InternalNode"),
        ("InternalNode", "LeafNode"),
        ("InternalNode", "InternalNode"),
    },
    "ENABLES": {
        ("LeafNode", "LeafNode"),
        ("LeafNode", "InternalNode"),
        ("InternalNode", "LeafNode"),
        ("InternalNode", "InternalNode"),
    },
    "SUPERSEDES": {
        ("LeafNode", "LeafNode"),
        ("LeafNode", "InternalNode"),
        ("InternalNode", "LeafNode"),
        ("InternalNode", "InternalNode"),
    },
    "REFERENCES": {
        ("OrganizationNode", "ModuleNode"),
        ("OrganizationNode", "InternalNode"),
        ("OrganizationNode", "LeafNode"),
    },
}

# User-visible node tables (excludes OrganizationNode)
USER_SPACE_TABLES = ["ModuleNode", "InternalNode", "LeafNode"]

# All node tables in the system
ALL_NODE_TABLES = ["ModuleNode", "InternalNode", "LeafNode", "OrganizationNode"]
