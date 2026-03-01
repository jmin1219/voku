"""
Background trace processing — annotations + temporal connections.

Extracted from chat.py so it's independently importable and testable
without triggering FastAPI dependency initialization.

Called by chat.py after response stream completes.
"""

from datetime import datetime, timezone

from app.services.storage.models import Trace, Connection
from app.services.storage.sqlite_trace import SQLiteTraceStorage
from app.services.annotation import AnnotationExtractionService
from app.services.connections import ConnectionService


async def process_traces_background(
    user_trace: Trace,
    assistant_trace: Trace,
    conversation_id: str,
    storage: SQLiteTraceStorage,
    annotation_service: AnnotationExtractionService,
    connection_service: ConnectionService,
) -> None:
    """Extract annotations and compute temporal connections for new traces.

    Runs after the response stream completes. Non-blocking.
    Failures are logged but never surface to the user.

    Args:
        user_trace: The user's message trace (already stored).
        assistant_trace: The assistant's response trace (already stored).
        conversation_id: Groups traces into a session.
        storage: Trace storage for reading context and writing annotations.
        annotation_service: LLM-based annotation extractor.
        connection_service: Computes typed connections between traces.
    """
    try:
        # --- Conversation context for better extraction ---
        context_traces = storage.get_traces_by_conversation(conversation_id)
        # Exclude the two traces we're about to annotate
        exclude = {user_trace.id, assistant_trace.id}
        context = [t for t in context_traces if t.id not in exclude][-4:]

        # --- Extract annotations ---
        user_annotations = await annotation_service.extract(user_trace, context)
        for ann in user_annotations:
            storage.store_annotation(ann)

        asst_context = context + [user_trace]
        asst_annotations = await annotation_service.extract(assistant_trace, asst_context)
        for ann in asst_annotations:
            storage.store_annotation(ann)

        # --- Temporal connections ---
        now = datetime.now(timezone.utc).isoformat()

        # parent → user_trace (if parent exists)
        if user_trace.parent_trace_id:
            storage.store_connection(Connection(
                source_id=user_trace.parent_trace_id,
                target_id=user_trace.id,
                type="temporal",
                weight=1.0,
                created_at=now,
            ))

        # user_trace → assistant_trace
        storage.store_connection(Connection(
            source_id=user_trace.id,
            target_id=assistant_trace.id,
            type="temporal",
            weight=1.0,
            created_at=now,
        ))

    except Exception:
        # Background failures are silent — traces are already stored,
        # annotations and connections are enrichment, not critical path.
        pass
