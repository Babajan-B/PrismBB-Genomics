"""Grounded chat endpoint — agent query interface."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.agents.orchestrator import OrchestratorAgent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    job_id: Optional[str] = None
    history: list = []


@router.post("")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Grounded agent chat. Ask questions about variants, rankings, genes, or literature.
    All answers are sourced from computed evidence stored in the database.
    """
    if not request.message.strip():
        raise HTTPException(400, "Message cannot be empty")

    agent = OrchestratorAgent(db)
    result = await agent.chat(
        user_message=request.message,
        job_id=request.job_id,
        chat_history=request.history,
    )
    return result
