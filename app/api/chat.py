"""
Chat API: POST /chat - accepts query and optional country, returns RAG response.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.pipeline import run_rag

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question")
    country: str | None = Field(None, description="User country for regional filtering")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Assistant answer")


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Run RAG pipeline and return assistant answer."""
    result = run_rag(query=request.query, country=request.country)
    return ChatResponse(response=result.response)
