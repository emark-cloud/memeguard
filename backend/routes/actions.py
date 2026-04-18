"""Trade action approval/rejection endpoints."""

import json
from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from database import get_db

router = APIRouter(tags=["actions"])


class ActionResponse(BaseModel):
    action_id: int
    # Optional overrides set by the confirm-trade modal. For buy actions the
    # user can adjust the proposed BNB amount; for sell actions they can
    # choose to only sell a fraction (0 < f <= 1) of their holdings.
    amount_bnb: float | None = Field(default=None, gt=0)
    sell_fraction: float | None = Field(default=None, gt=0, le=1)


class RejectRequest(BaseModel):
    action_id: int
    # Optional free-text reason the user gave for rejecting. Cap the length
    # so a runaway client can't push arbitrary blobs into the DB.
    reason: str | None = Field(default=None, max_length=500)


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
    # Phase 1: DB operations — fetch, mark approved, commit, close
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pending_actions WHERE id = ? AND status = 'pending'",
            (req.action_id,),
        )
        action = await cursor.fetchone()
        if not action:
            return JSONResponse(content={"error": "Action not found or already resolved"}, status_code=404)

        action_dict = dict(action)
        now = datetime.now(timezone.utc).isoformat()

        # Apply confirm-modal overrides before execution.
        if action_dict["action_type"] == "buy" and req.amount_bnb is not None:
            from database import get_all_config
            cfg = await get_all_config()
            min_bnb = float(cfg.get("min_per_trade_bnb", 0.002))
            max_bnb = float(cfg.get("max_per_trade_bnb", 0.05))
            if req.amount_bnb < min_bnb or req.amount_bnb > max_bnb:
                return JSONResponse(
                    content={"error": f"amount_bnb must be between {min_bnb} and {max_bnb}"},
                    status_code=400,
                )
            action_dict["amount_bnb"] = req.amount_bnb
            await db.execute(
                "UPDATE pending_actions SET amount_bnb = ? WHERE id = ?",
                (req.amount_bnb, req.action_id),
            )

        if action_dict["action_type"] == "sell" and req.sell_fraction is not None:
            # Stash the fraction in tx_preview so the executor can scale the
            # on-chain balance without another round-trip.
            try:
                preview = json.loads(action_dict.get("tx_preview") or "{}")
            except (json.JSONDecodeError, TypeError):
                preview = {}
            preview["sell_fraction"] = req.sell_fraction
            action_dict["tx_preview"] = json.dumps(preview)
            await db.execute(
                "UPDATE pending_actions SET tx_preview = ? WHERE id = ?",
                (action_dict["tx_preview"], req.action_id),
            )

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

        # Track override: user approved a RED or AMBER signal (overriding agent caution)
        if action["risk_score"] in ("red", "amber"):
            await db.execute(
                "INSERT INTO overrides (token_address, agent_recommendation, user_action, created_at) VALUES (?, ?, ?, ?)",
                (action["token_address"], "skip", "approved", now),
            )

        await db.commit()
    finally:
        await db.close()

    # Phase 2: Execute trade (DB connection is released)
    from services.approval_gate import mark_session_approved
    mark_session_approved()

    from main import ws_manager
    from services.executor import execute_approved_action
    result = await execute_approved_action(action_dict, ws_manager)

    return {"status": "approved", "action_id": req.action_id, "result": result}


@router.post("/actions/reject")
async def reject_action(req: RejectRequest):
    """Reject a pending trade action, optionally with a free-text reason."""
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
        reason = req.reason.strip() if req.reason else None
        if reason == "":
            reason = None

        await db.execute(
            "UPDATE pending_actions SET status = 'rejected', resolved_at = ?, rejection_reason = ? WHERE id = ?",
            (now, reason, req.action_id),
        )

        # Check if this was an override (rejecting agent's buy recommendation)
        if action["action_type"] == "buy" and action["risk_score"] == "green":
            await db.execute(
                "INSERT INTO overrides (token_address, agent_recommendation, user_action, created_at) VALUES (?, ?, ?, ?)",
                (action["token_address"], "buy", "rejected", now),
            )

        detail: dict[str, object] = {"action_id": req.action_id}
        if reason:
            detail["reason"] = reason
        await db.execute(
            "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
            ("reject", action["token_address"], json.dumps(detail), now),
        )
        await db.commit()

        return {"status": "rejected", "action_id": req.action_id}
    finally:
        await db.close()
