"""
Chat API routes — v2 trace-based conversation.

Every message (user and assistant) becomes an immutable trace.
Traces are embedded on creation for immediate retrieval.
Context assembly builds system prompts from the trace graph.

v2 replaces ConversationService with direct trace storage.
Conversations are implicit groupings via conversation_id.
"""

import json
import uuid
from datetime import datetime, timezone

import anthropic
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from app.config import settings
from app.dependencies import (
    trace_storage, trace_context, embedder,
    annotation_service, connection_service,
)
from app.services.storage.models import Trace
from app.services.background import process_traces_background


router = APIRouter(prefix="/api", tags=["api"])


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    messages: list[dict]  # [{"role": "user", "content": "..."}]


@router.post("/chat")
async def chat(request: ChatRequest):
    """Stream a response from Anthropic with trace-based context.

    Flow:
      1. Create conversation_id if new
      2. Store user message as trace + embed
      3. Build context from trace graph
      4. Stream response from Anthropic
      5. Store assistant response as trace + embed
    """
    now = datetime.now(timezone.utc).isoformat()

    # Create or reuse conversation
    if request.conversation_id is None:
        conversation_id = str(uuid.uuid4())
    else:
        conversation_id = request.conversation_id

    # Validate last message is from user
    last_message = request.messages[-1]
    if last_message.get("role") != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")

    # Determine parent trace (last trace in this conversation, if any)
    existing_traces = trace_storage.get_traces_by_conversation(conversation_id)
    parent_id = existing_traces[-1].id if existing_traces else None

    # Store user message as trace
    user_trace = Trace(
        id=str(uuid.uuid4()),
        timestamp=now,
        content=last_message["content"],
        conversation_id=conversation_id,
        parent_trace_id=parent_id,
        source="user",
    )
    trace_storage.store_trace(user_trace)

    # Embed user trace immediately (enables retrieval in future conversations)
    user_embedding = embedder.embed(user_trace.content)
    trace_storage.store_embedding(user_trace.id, user_embedding, embedder.model_name)

    # Build context-aware system prompt from trace graph
    system_prompt, retrieval_ids = trace_context.build_system_prompt(
        last_message["content"]
    )

    # Stream from Anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Mutable container — generate() writes, background task reads
    trace_holder: dict = {}

    def generate():
        # First line: JSON metadata (retrieval IDs + conversation ID)
        yield json.dumps({
            "conversation_id": conversation_id,
            "retrieval_ids": retrieval_ids,
        }) + "\n"

        buffer = []
        try:
            stream_kwargs = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": request.messages,
            }
            if system_prompt:
                stream_kwargs["system"] = system_prompt

            with client.messages.stream(**stream_kwargs) as stream:
                for text in stream.text_stream:
                    buffer.append(text)
                    yield text

            # Stream complete — store assistant response as trace + embed
            full_response = "".join(buffer)
            asst_now = datetime.now(timezone.utc).isoformat()
            assistant_trace = Trace(
                id=str(uuid.uuid4()),
                timestamp=asst_now,
                content=full_response,
                conversation_id=conversation_id,
                parent_trace_id=user_trace.id,
                source="assistant",
            )
            trace_storage.store_trace(assistant_trace)

            asst_embedding = embedder.embed(full_response)
            trace_storage.store_embedding(
                assistant_trace.id, asst_embedding, embedder.model_name
            )

            # Pass to background task
            trace_holder["assistant"] = assistant_trace

        except Exception:
            # If streaming fails, user trace is still stored (immutable)
            raise

    async def _run_background():
        """Runs after response stream completes. Extracts annotations + connections."""
        assistant_trace = trace_holder.get("assistant")
        if assistant_trace is None:
            return  # Stream failed — nothing to process
        await process_traces_background(
            user_trace=user_trace,
            assistant_trace=assistant_trace,
            conversation_id=conversation_id,
            storage=trace_storage,
            annotation_service=annotation_service,
            connection_service=connection_service,
        )

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={"X-Conversation-Id": conversation_id},
        background=BackgroundTask(_run_background),
    )


@router.post("/conversations")
def create_conversation():
    """Create a new conversation ID. Called when user clicks +new."""
    conversation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    return {"id": conversation_id, "created_at": now}


@router.get("/history")
def history():
    """Return all conversations with their traces (as messages)."""
    conversations = trace_storage.list_conversations()
    result = []
    for conv in conversations:
        traces = trace_storage.get_traces_by_conversation(conv["id"])
        result.append({
            "id": conv["id"],
            "created_at": conv["first_trace_at"],
            "updated_at": conv["last_trace_at"],
            "messages": [
                {
                    "id": t.id,
                    "role": t.source,  # 'user' | 'assistant'
                    "content": t.content,
                    "thinking": None,  # v2 doesn't store thinking separately
                    "created_at": t.timestamp,
                }
                for t in traces
            ],
        })
    return result


@router.get("/status")
def status():
    """Basic API status check."""
    return {
        "status": "ok",
        "architecture": "traces",
        "version": "2.0.0",
    }
