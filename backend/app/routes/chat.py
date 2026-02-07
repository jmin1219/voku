"""
Chat API routes - handles conversation input and graph updates.
"""
from fastapi import APIRouter, HTTPException
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
async def process_chat(request: ChatRequest) -> ChatResponse:
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
    # TODO: Wire up ChatService
    raise HTTPException(status_code=501, detail="Not implemented yet")
