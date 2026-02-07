"""
Chat API routes - handles conversation input and graph updates.
"""

from app.dependencies import get_chat_service
from app.services.chat import ChatService
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    text: str = Field(..., min_length=1, description="User's message text")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    node_ids: list[str] = Field(description="Created node IDs")
    propositions: list[dict] = Field(description="Extracted propositions with metadata")


@router.post("/", response_model=ChatResponse)
async def process_chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(
        get_chat_service
    ),  # Inject ChatService dependency
) -> ChatResponse:
    """
    Process user text and create graph nodes.

    Flow:
    1. Extract propositions from text
    2. Semantic deduplication (cosine similarity > 0.95)
    3. Create LeafNodes in graph
    4. Create SIMILAR_TO edges

    Args:
        request: User's message text

    Returns:
        Created node IDs and extracted propositions
    """
    try:
        # Call ChatService to process the chat input
        result = await chat_service.process_message(request.text)

        # Format response with node IDs and proposition details
        return ChatResponse(
            node_ids=result.node_ids,
            propositions=[
                {
                    "proposition": prop.proposition,
                    "node_purpose": prop.node_purpose,
                    "confidence": prop.confidence,
                    "source_type": prop.source_type,
                }
                for prop in result.propositions
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
