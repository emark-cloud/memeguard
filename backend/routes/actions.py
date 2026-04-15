"""Trade action approval/rejection endpoints."""

import json
from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import get_db

router = APIRouter(tags=["actions"])


class ActionResponse(BaseModel):
    action_id: int


@router.get("/actions/pending")
async def list_pending_actions():
    """Get all pending actions awaiting approval."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pending_actions WHERE status = 'pending' ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


@router.post("/actions/approve")
async def approve_action(req: ActionResponse):
    """Approve a pending trade action."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pending_actions WHERE id = ? AND status = 'pending'",
            (req.action_id,),
        )
        action = await cursor.fetchone()
        if not action:
            return JSONResponse(content={"error": "Action not found or already resolved"}, status_code=404)

        now = datetime.now(timezone.utc).isoformat()

        # Mark as approved
        await db.execute(
            "UPDATE pending_actions SET status = 'approved', resolved_at = ? WHERE id = ?",
            (now, req.action_id),
        )

        # Log activity
        await db.execute(
            "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
            ("approve", action["token_address"], json.dumps({"action_id": req.action_id}), now),
        )
        await db.commit()

        # Mark session as approved for per-session mode
        from services.approval_gate import mark_session_approved
        mark_session_approved()

        # Trigger execution (imported here to avoid circular imports)
        from services.executor import execute_approved_action
        result = await execute_approved_action(dict(action))

        return {"status": "approved", "action_id": req.action_id, "result": result}
    finally:
        await db.close()


@router.post("/actions/reject")
async def reject_action(req: ActionResponse):
    """Reject a pending trade action."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pending_actions WHERE id = ? AND status = 'pending'",
            (req.action_id,),
        )
        action = await cursor.fetchone()
        if not action:
            return JSONResponse(content={"error": "Action not found or already resolved"}, status_code=404)

        now = datetime.now(timezone.utc).isoformat()

        await db.execute(
            "UPDATE pending_actions SET status = 'rejected', resolved_at = ? WHERE id = ?",
            (now, req.action_id),
        )

        # Check if this was an override (rejecting agent's buy recommendation)
        if action["action_type"] == "buy" and action["risk_score"] == "green":
            await db.execute(
                "INSERT INTO overrides (token_address, agent_recommendation, user_action, created_at) VALUES (?, ?, ?, ?)",
                (action["token_address"], "buy", "rejected", now),
            )

        await db.execute(
            "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
            ("reject", action["token_address"], json.dumps({"action_id": req.action_id}), now),
        )
        await db.commit()

        return {"status": "rejected", "action_id": req.action_id}
    finally:
        await db.close()
