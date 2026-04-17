"""AI advisor chat endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    # Cap prompt size so a runaway client can't push a 10MB body into Gemini.
    message: str = Field(min_length=1, max_length=2000)
    token_address: str | None = Field(default=None, max_length=64)


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
