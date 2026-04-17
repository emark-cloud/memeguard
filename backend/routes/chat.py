"""AI advisor chat endpoint."""

from fastapi import APIRouter, Query
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


@router.get("/chat/history")
async def get_history(token_address: str | None = Query(None)):
    """Return persisted chat messages for the given scope (global if unset)."""
    from database import get_db
    db = await get_db()
    try:
        if token_address is None:
            cursor = await db.execute(
                "SELECT id, role, content, created_at FROM chat_messages "
                "WHERE token_address IS NULL ORDER BY id ASC"
            )
        else:
            cursor = await db.execute(
                "SELECT id, role, content, created_at FROM chat_messages "
                "WHERE token_address = ? ORDER BY id ASC",
                (token_address,),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


@router.delete("/chat/history")
async def clear_history(
    token_address: str | None = Query(None),
    scope: str = Query("current", pattern="^(current|all)$"),
):
    """Clear chat history.

    Defaults to 'current': wipes either global chat (if token_address omitted)
    or a single token's chat. Pass scope=all to wipe every scope.
    """
    from services.chat_service import clear_chat_history
    await clear_chat_history(token_address=token_address, scope=scope)
    return {"status": "ok"}
