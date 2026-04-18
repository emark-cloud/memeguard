"""Position tracking endpoints."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from database import get_db


class ManualSellRequest(BaseModel):
    sell_fraction: float | None = Field(default=None, gt=0, le=1)

router = APIRouter(tags=["positions"])


@router.get("/positions")
async def list_positions(
    status: str | None = Query("active", description="Filter: active/closed/all"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get positions with PnL."""
    db = await get_db()
    try:
        if status == "all":
            cursor = await db.execute(
                """SELECT p.*, t.name as token_name, t.symbol as token_symbol
                   FROM positions p LEFT JOIN tokens t ON p.token_address = t.address
                   ORDER BY p.opened_at DESC LIMIT ?""", (limit,)
            )
        else:
            cursor = await db.execute(
                """SELECT p.*, t.name as token_name, t.symbol as token_symbol
                   FROM positions p LEFT JOIN tokens t ON p.token_address = t.address
                   WHERE p.status = ? ORDER BY p.opened_at DESC LIMIT ?""",
                (status, limit),
            )
        rows = await cursor.fetchall()
        positions = [dict(row) for row in rows]

        # Attach pending sell actions to active positions
        for pos in positions:
            if pos["status"] == "active":
                sell_cursor = await db.execute(
                    "SELECT * FROM pending_actions WHERE token_address = ? AND action_type = 'sell' AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
                    (pos["token_address"],),
                )
                sell_action = await sell_cursor.fetchone()
                pos["pending_sell"] = dict(sell_action) if sell_action else None
            else:
                pos["pending_sell"] = None

        return positions
    finally:
        await db.close()


@router.post("/positions/{position_id}/sell")
async def manual_sell(position_id: int, req: ManualSellRequest | None = None):
    """User-initiated sell on an active position.

    The click itself is the approval, so we create the pending_action, mark it
    approved, and hand off to the executor in one request. If a sell is already
    pending for this token, surface that action instead of racing a duplicate.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM positions WHERE id = ? AND status = 'active'",
            (position_id,),
        )
        position = await cursor.fetchone()
        if not position:
            return JSONResponse(
                content={"error": "Position not found or not active"},
                status_code=404,
            )
        pos = dict(position)

        # Don't race the auto-propose path — if a sell is already pending,
        # just return it so the client can reuse the existing approval flow.
        cursor = await db.execute(
            "SELECT id FROM pending_actions WHERE token_address = ? "
            "AND action_type = 'sell' AND status = 'pending' "
            "ORDER BY id DESC LIMIT 1",
            (pos["token_address"],),
        )
        existing = await cursor.fetchone()
        if existing:
            return JSONResponse(
                content={"error": "Sell already pending for this position",
                         "action_id": existing["id"]},
                status_code=409,
            )

        now = datetime.now(timezone.utc).isoformat()
        sell_fraction = req.sell_fraction if req and req.sell_fraction is not None else 1.0
        preview = {"token_amount": pos.get("token_quantity", 0) or 0, "sell_fraction": sell_fraction}
        cursor = await db.execute(
            """INSERT INTO pending_actions (token_address, action_type, amount_bnb, slippage,
               persona, risk_score, rationale, tx_preview, status, resolved_at, created_at)
               VALUES (?, 'sell', ?, 5.0, ?, ?, ?, ?, 'approved', ?, ?)""",
            (
                pos["token_address"],
                pos.get("entry_amount_bnb", 0) or 0,
                "manual",
                pos.get("entry_risk_score", "") or "",
                f"[MANUAL] User-initiated sell ({int(sell_fraction * 100)}%) from Positions page",
                json.dumps(preview),
                now,
                now,
            ),
        )
        action_id = cursor.lastrowid
        cursor = await db.execute(
            "SELECT * FROM pending_actions WHERE id = ?", (action_id,)
        )
        action = await cursor.fetchone()
        action_dict = dict(action) if action else {}

        await db.execute(
            "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
            (
                "approve",
                pos["token_address"],
                json.dumps({"action_id": action_id, "source": "manual"}),
                now,
            ),
        )
        await db.commit()
    finally:
        await db.close()

    from main import ws_manager
    from services.executor import execute_approved_action
    result = await execute_approved_action(action_dict, ws_manager)

    if result.get("status") != "executed":
        db2 = await get_db()
        try:
            await db2.execute(
                "UPDATE pending_actions SET status = 'failed' WHERE id = ?",
                (action_id,),
            )
            await db2.commit()
        finally:
            await db2.close()
        return JSONResponse(
            content={"status": "failed", "action_id": action_id, "result": result},
            status_code=502,
        )

    return {"status": "executed", "action_id": action_id, "result": result}


@router.post("/positions/{position_id}/abandon")
async def abandon_position(position_id: int):
    """Close a dust position without an on-chain sell.

    Four.meme enforces a 0.001 BNB minimum fee per sell, so tiny positions
    (< ~0.002 BNB entry) revert on sellToken because the fee exceeds
    proceeds. This endpoint lets the user write off the position so the
    Positions page stops surfacing a button that can never succeed.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM positions WHERE id = ? AND status = 'active'",
            (position_id,),
        )
        position = await cursor.fetchone()
        if not position:
            return JSONResponse(
                content={"error": "Position not found or not active"},
                status_code=404,
            )
        pos = dict(position)
        entry = float(pos.get("entry_amount_bnb") or 0)
        now = datetime.now(timezone.utc).isoformat()

        await db.execute(
            """UPDATE positions SET status = 'closed', exit_price = 0,
               exit_amount_bnb = 0, pnl_bnb = ?, closed_at = ? WHERE id = ?""",
            (round(-entry, 8), now, position_id),
        )
        await db.execute(
            "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
            (
                "position_abandoned",
                pos["token_address"],
                json.dumps({"position_id": position_id, "written_off_bnb": entry}),
                now,
            ),
        )
        await db.commit()
    finally:
        await db.close()

    return {"status": "abandoned", "position_id": position_id, "written_off_bnb": entry}


@router.get("/trades/daily")
async def daily_trade_stats():
    """Get today's trade count and total BNB spent."""
    db = await get_db()
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount_bnb), 0) as spent, COUNT(*) as count FROM trades WHERE executed_at >= ?",
            (today,),
        )
        row = await cursor.fetchone()
        return {
            "spent_today_bnb": round(row["spent"], 6),
            "trades_today": row["count"],
        }
    finally:
        await db.close()
