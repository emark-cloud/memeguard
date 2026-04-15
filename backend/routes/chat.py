"""AI advisor chat endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    token_address: str | None = None


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat")
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """Send a message to the AI trading advisor."""
    from services.chat_service import chat
    reply = await chat(req.message, req.token_address)
    return ChatResponse(reply=reply)


@router.delete("/chat/history")
async def clear_history():
    """Clear the chat conversation history."""
    from services.chat_service import clear_chat_history
    clear_chat_history()
    return {"status": "ok"}
