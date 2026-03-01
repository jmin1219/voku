"""
v2 Storage data models — shared between storage implementations.

Two dataclasses mirroring the trace-based architecture:
- Trace: immutable ground truth (maps to traces table)
- SimilarTrace: a trace returned from vector search with its similarity score

Design: SPEC.md § Data Model, Layer 1.
Constraint 2.8: No classification at storage level. Annotations handle that (Phase 2).
Constraint 2.11: Traces are immutable — no update methods exist by design.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Annotation:
    """A computed annotation on a trace — re-extractable, category-free.

    Annotations are the intelligence layer over immutable traces.
    Types and keys are free text — no predefined categories at the
    schema level. Structure emerges from what the extraction model finds.

    Maps 1:1 to the annotations table in v2_schema.sql.

    Speech act types (Austin/Searle) guide extraction:
      Asserting  → measurables, facts, beliefs
      Committing → commitments, plans, goals
      Expressing → emotions, evaluations
      Declaring  → decisions, definitions
    """

    id: str                        # UUID4
    trace_id: str                  # Which trace this annotates
    type: str                      # Free text: 'measurable' | 'commitment' | 'decision' | 'emotion' | 'topic' | ...
    key: Optional[str] = None     # What was measured/committed/decided/felt
    value: Optional[str] = None   # The extracted value
    confidence: Optional[float] = None
    extracted_at: str = ""         # ISO 8601
    extractor: str = ""            # Model/version that produced this


@dataclass
class Connection:
    """A typed relationship between two traces.

    Four connection types (SPEC.md § Data Model, Layer 3):
      semantic:    computed from embedding cosine similarity (k-NN)
      temporal:    sequential traces in a session
      intentional: user or system links across sessions
      supersedes:  a later trace replaces an earlier understanding

    Semantic connections recompute when embeddings change.
    Intentional connections are permanent.
    """

    source_id: str              # Trace ID
    target_id: str              # Trace ID
    type: str                   # 'semantic' | 'temporal' | 'intentional' | 'supersedes'
    weight: Optional[float] = None  # Cosine similarity for semantic, 1.0 for temporal
    created_at: str = ""        # ISO 8601


@dataclass
class Trace:
    """An immutable conversational trace — the atomic unit of Voku v2.

    Every message in every conversation becomes a trace. Once stored,
    the content and timestamp are never modified. All intelligence
    (annotations, connections, embeddings) is computed on top of traces
    and can be recomputed without changing the ground truth.

    Maps 1:1 to the traces table in v2_schema.sql.
    """

    id: str                                  # UUID4, generated at creation
    timestamp: str                           # ISO 8601, when the trace was created
    content: str                             # Raw text, never modified after storage
    conversation_id: Optional[str] = None    # Groups traces into sessions
    parent_trace_id: Optional[str] = None    # Previous trace in the conversation thread
    source: str = "user"                     # 'user' | 'assistant' | 'resource' | 'system'


@dataclass
class SimilarTrace:
    """A trace returned from similarity search, paired with its cosine score.

    Used by find_similar() to return ranked results from vector search.
    Score range: 0.0 (unrelated) to 1.0 (identical embedding).
    """

    trace: Trace
    score: float
