"""Position tracker — background job that updates prices and computes PnL for active positions."""

import asyncio
import json
from datetime import datetime, timezone

from database import get_db
from clients.bsc_web3 import BSCWeb3Client


async def start_position_tracker(ws_manager, interval: int = 60):
    """Periodically update active position prices and PnL."""
    web3 = BSCWeb3Client()

    try:
        while True:
            try:
                await update_positions(web3, ws_manager)
            except Exception as e:
                print(f"[PositionTracker] Error: {e}")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass


async def update_positions(web3: BSCWeb3Client, ws_manager):
    """Fetch current prices for all active positions and update PnL."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM positions WHERE status = 'active'")
        positions = [dict(row) for row in await cursor.fetchall()]

        if not positions:
            return

        now = datetime.now(timezone.utc).isoformat()

        for pos in positions:
            try:
                info = web3.get_token_info(pos["token_address"])
                if not info:
                    continue

                last_price = info.get("lastPrice", 0)
                current_price = last_price / 10**18 if last_price else 0

                entry_price = pos.get("entry_price", 0) or 0
                entry_amount = pos.get("entry_amount_bnb", 0) or 0
                token_qty = pos.get("token_quantity", 0) or 0

                # PnL = (current_value - entry_cost)
                current_value = token_qty * current_price if current_price > 0 else 0
                pnl = current_value - entry_amount

                await db.execute(
                    "UPDATE positions SET current_price = ?, pnl_bnb = ? WHERE id = ?",
                    (current_price, round(pnl, 8), pos["id"]),
                )

                # Broadcast position update
                if ws_manager:
                    await ws_manager.broadcast("position_update", {
                        "position_id": pos["id"],
                        "token_address": pos["token_address"],
                        "current_price": current_price,
                        "pnl_bnb": round(pnl, 8),
                        "entry_amount_bnb": entry_amount,
                    })

                # Check exit conditions
                if entry_amount > 0:
                    pnl_pct = (pnl / entry_amount) * 100
                    if pnl_pct >= 100:
                        await _propose_exit(db, pos, "take_profit", f"2x profit reached ({pnl_pct:.0f}%)", ws_manager)
                    elif pnl_pct <= -50:
                        await _propose_exit(db, pos, "stop_loss", f"50% loss ({pnl_pct:.0f}%)", ws_manager)

            except Exception as e:
                print(f"[PositionTracker] Error updating {pos['token_address']}: {e}")

        await db.commit()
    finally:
        await db.close()


async def _propose_exit(db, position: dict, reason_type: str, rationale: str, ws_manager):
    """Create a pending sell action for position exit."""
    now = datetime.now(timezone.utc).isoformat()

    # Check if there's already a pending exit for this position
    cursor = await db.execute(
        "SELECT id FROM pending_actions WHERE token_address = ? AND action_type = 'sell' AND status = 'pending'",
        (position["token_address"],),
    )
    if await cursor.fetchone():
        return

    await db.execute(
        """INSERT INTO pending_actions (token_address, action_type, amount_bnb, slippage,
           persona, risk_score, rationale, tx_preview, status, created_at)
           VALUES (?, 'sell', ?, 5.0, ?, ?, ?, ?, 'pending', ?)""",
        (
            position["token_address"],
            position["entry_amount_bnb"],
            "",
            position.get("entry_risk_score", ""),
            f"[{reason_type.upper()}] {rationale}",
            json.dumps({"token_amount": position.get("token_quantity", 0)}),
            now,
        ),
    )

    if ws_manager:
        await ws_manager.broadcast("action_proposed", {
            "token_address": position["token_address"],
            "action_type": "sell",
            "reason": reason_type,
            "rationale": rationale,
        })
