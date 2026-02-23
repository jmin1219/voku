"""
Chat API routes — live conversation with Anthropic streaming.

Build 2: POST /chat streams responses, persists messages.
         GET /history returns stored conversations.
Build 3: Context assembly — retrieval injects prior propositions into system prompt.
"""

import json

import anthropic
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.services.conversation.service import ConversationService
from app.dependencies import retrieval as _retrieval

router = APIRouter(prefix="/api", tags=["api"])


def _build_system_prompt(user_message: str, limit: int = 5) -> tuple[str | None, list[str]]:
    """Retrieve relevant propositions and format as system context.

    Returns:
        (system_prompt, retrieval_ids) — prompt may be None if no results.
        retrieval_ids is always a list (possibly empty).
    """
    results = _retrieval.retrieve(
        query=user_message,
        limit=limit,
        temporal_weight=0.3,
        similarity_threshold=0.45,
    )
    if not results:
        return None, []

    retrieval_ids = [r.proposition_id for r in results]

    context_lines = []
    for r in results:
        context_lines.append(f"- [{r.node_type}] {r.text} (confidence: {r.confidence:.1f})")

    system = (
        "You are Voku, a personal context engine. You have access to the user's "
        "prior knowledge — propositions extracted from their past conversations. "
        "Use this context naturally to inform your responses. Don't list the propositions "
        "back to the user — weave the knowledge into your response as if you already know them.\n\n"
        "## Relevant context from prior conversations:\n"
        + "\n".join(context_lines)
    )

    return system, retrieval_ids


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    messages: list[dict]  # [{"role": "user", "content": "..."}]


@router.post("/chat")
async def chat(request: ChatRequest):
    """Stream a response from Anthropic with retrieved context."""
    service = ConversationService(settings.db_path)

    # Create or reuse conversation
    if request.conversation_id is None:
        conv = service.create_conversation()
        conversation_id = conv.id
    else:
        conversation_id = request.conversation_id

    # Persist user message immediately
    last_message = request.messages[-1]
    if last_message.get("role") != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")
    service.add_message(conversation_id, role="user", content=last_message["content"])

    # Build context-aware system prompt from retrieved propositions
    system_prompt, retrieval_ids = _build_system_prompt(last_message["content"])

    # Stream from Anthropic, persist assistant message after completion
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def generate():
        # First line: JSON metadata with retrieval IDs
        # Frontend parses this before switching to text stream mode
        yield json.dumps({"retrieval_ids": retrieval_ids}) + "\n"

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
            # Stream complete — persist full response
            full_response = "".join(buffer)
            service.add_message(
                conversation_id, role="assistant", content=full_response
            )
        finally:
            service.close()

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={"X-Conversation-Id": conversation_id},
    )


@router.post("/conversations")
def create_conversation():
    """Create an empty conversation. Called when user clicks +new."""
    service = ConversationService(settings.db_path)
    try:
        conv = service.create_conversation()
        return {"id": conv.id, "created_at": conv.created_at}
    finally:
        service.close()


@router.get("/history")
def history():
    """Return all conversations with their messages."""
    service = ConversationService(settings.db_path)
    try:
        conversations = service.list_conversations()
        result = []
        for conv in conversations:
            messages = service.get_conversation_messages(conv.id)
            result.append({
                "id": conv.id,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "thinking": msg.thinking,
                        "created_at": msg.created_at,
                    }
                    for msg in messages
                ],
            })
        return result
    finally:
        service.close()


@router.get("/status")
def status():
    """Basic API status check."""
    return {"status": "ok", "architecture": "sqlite", "version": "0.4.0"}
