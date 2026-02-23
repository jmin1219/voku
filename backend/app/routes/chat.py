"""
Chat API routes — live conversation with Anthropic streaming.

Build 2: POST /chat streams responses, persists messages.
         GET /history returns stored conversations.
Build 3: Context assembly — retrieval injects prior propositions into system prompt.
Build 4: Context assembly v2 — user model + annotated retrieval via ContextAssemblyV2.
"""

import json

import anthropic
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.services.conversation.service import ConversationService
from app.dependencies import context_assembly


router = APIRouter(prefix="/api", tags=["api"])


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    messages: list[dict]  # [{"role": "user", "content": "..."}]


@router.post("/chat")
async def chat(request: ChatRequest):
    """Stream a response from Anthropic with model-aware context."""
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

    # Build context-aware system prompt from user model + retrieved propositions
    system_prompt, retrieval_ids = context_assembly.build_system_prompt(
        last_message["content"]
    )

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
