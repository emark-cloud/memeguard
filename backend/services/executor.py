"""Trade executor — executes approved actions via Four.meme CLI."""

import asyncio
import json
from datetime import datetime, timezone
from database import get_db


async def execute_approved_action(action: dict, ws_manager=None) -> dict:
    """Execute a trade that was approved by the user."""
    from clients.fourmeme_cli import FourMemeCLI

    cli = FourMemeCLI()
    now = datetime.now(timezone.utc).isoformat()
    db = await get_db()

    try:
        action_type = action["action_type"]
        token_address = action["token_address"]
        amount_bnb = float(action["amount_bnb"])

        # Look up token name for display
        cursor = await db.execute("SELECT name FROM tokens WHERE address = ?", (token_address,))
        token_row = await cursor.fetchone()
        token_name = token_row["name"] if token_row else token_address[:10] + "..."

        if action_type == "buy":
            # Re-validate budget at execute time. A stale action queued before
            # other trades filled can push the day over cap; trust only the DB.
            from database import get_all_config
            cfg = await get_all_config()
            min_per_trade = float(cfg.get("min_per_trade_bnb", 0.002))
            max_per_trade = float(cfg.get("max_per_trade_bnb", 0.05))
            max_per_day = float(cfg.get("max_per_day_bnb", 0.3))
            # Four.meme charges min 0.001 BNB fee per sell — if a buy is too
            # small, the sell will revert with "Gw" because the fee exceeds
            # proceeds. Floor the buy so round-trip is always viable.
            if amount_bnb < min_per_trade:
                return {
                    "status": "rejected",
                    "message": f"amount {amount_bnb} BNB below min_per_trade ({min_per_trade}); sell would be blocked by Four.meme min fee",
                }
            if amount_bnb > max_per_trade:
                return {
                    "status": "rejected",
                    "message": f"amount {amount_bnb} BNB exceeds max_per_trade ({max_per_trade})",
                }
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            cursor = await db.execute(
                "SELECT COALESCE(SUM(amount_bnb), 0) as spent FROM trades "
                "WHERE side = 'buy' AND executed_at >= ?",
                (today,),
            )
            spent_today = float((await cursor.fetchone())["spent"])
            if spent_today + amount_bnb > max_per_day:
                return {
                    "status": "rejected",
                    "message": f"would exceed max_per_day ({spent_today + amount_bnb:.4f} > {max_per_day})",
                }

            # Convert BNB to Wei
            funds_wei = str(int(amount_bnb * 10**18))

            # Get quote to compute min amount with slippage protection
            slippage_pct = float(action.get("slippage", 5))
            min_amount_wei = "0"
            estimated_tokens = 0
            try:
                quote = await cli.quote_buy(token_address, "0", funds_wei)
                if not isinstance(quote, dict):
                    quote = {}
                estimated_tokens = int(quote.get("estimatedAmount", 0) or quote.get("amount", 0) or 0)
                if estimated_tokens > 0:
                    min_amount_wei = str(int(estimated_tokens * (1 - slippage_pct / 100)))
            except Exception as e:
                print(f"[Executor] Quote failed, proceeding without slippage protection: {e}")

            result = await cli.buy_by_funds(token_address, funds_wei, min_amount_wei)

            tx_hash = result.get("txHash", result.get("hash", ""))
            if not tx_hash:
                # CLI reported success-shaped result with no hash — treat as failure
                # rather than writing a phantom position with an empty tx_hash.
                return {"status": "error", "message": f"CLI returned no tx_hash: {result}"}

            # CLI only returns txHash; get token quantity from the pre-buy quote
            # Convert from wei (18 decimals) to human-readable
            token_quantity = estimated_tokens / 10**18 if estimated_tokens > 0 else 0
            entry_price = amount_bnb / token_quantity if token_quantity > 0 else 0

            # Create position
            cursor = await db.execute(
                """INSERT INTO positions (token_address, entry_price, entry_amount_bnb,
                   token_quantity, status, entry_risk_score, opened_at)
                   VALUES (?, ?, ?, ?, 'active', ?, ?)""",
                (
                    token_address,
                    entry_price,
                    amount_bnb,
                    token_quantity,
                    action.get("risk_score", ""),
                    now,
                ),
            )
            position_id = cursor.lastrowid

            # Record trade
            await db.execute(
                """INSERT INTO trades (position_id, token_address, side, amount_bnb,
                   token_quantity, price, tx_hash, slippage, approval_mode, executed_at)
                   VALUES (?, ?, 'buy', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    position_id,
                    token_address,
                    amount_bnb,
                    token_quantity,
                    entry_price,
                    tx_hash,
                    float(action.get("slippage", 0)),
                    action.get("persona", ""),
                    now,
                ),
            )

            # Log activity
            await db.execute(
                "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
                ("trade_executed", token_address, json.dumps({"side": "buy", "amount_bnb": amount_bnb, "tx_hash": tx_hash}), now),
            )

            await db.commit()

            # Broadcast trade_executed
            if ws_manager:
                await ws_manager.broadcast("trade_executed", {
                    "token_address": token_address,
                    "token_name": token_name,
                    "side": "buy",
                    "amount_bnb": amount_bnb,
                    "tx_hash": tx_hash,
                    "position_id": position_id,
                })

            return {"status": "executed", "tx_hash": tx_hash, "position_id": position_id}

        elif action_type == "sell":
            # Extract token amount + optional fraction override from tx_preview
            token_amount = 0.0
            sell_fraction = 1.0
            tx_preview_str = action.get("tx_preview", "{}")
            if isinstance(tx_preview_str, str):
                try:
                    preview = json.loads(tx_preview_str)
                    token_amount = float(preview.get("token_amount", 0))
                    f = preview.get("sell_fraction")
                    if f is not None:
                        sell_fraction = max(0.0, min(1.0, float(f)))
                except (json.JSONDecodeError, ValueError):
                    pass

            if token_amount <= 0:
                return {"status": "error", "message": "No token amount to sell"}

            # Use exact on-chain balance to avoid floating-point precision loss
            from clients.bsc_web3 import BSCWeb3Client
            web3_client = BSCWeb3Client()
            on_chain_balance = await asyncio.to_thread(web3_client.get_token_balance, token_address)
            if on_chain_balance and on_chain_balance > 0:
                scaled = int(on_chain_balance * sell_fraction)
                if scaled <= 0:
                    return {"status": "error", "message": f"sell_fraction {sell_fraction} rounds to zero tokens"}
                amount_wei = str(scaled)
                token_amount = scaled / 10**18
            else:
                amount_wei = str(int(token_amount * sell_fraction * 10**18))

            # Look up the active position
            cursor = await db.execute(
                "SELECT * FROM positions WHERE token_address = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
                (token_address,),
            )
            position = await cursor.fetchone()
            position_id = position["id"] if position else None
            entry_amount = float(position["entry_amount_bnb"]) if position else amount_bnb

            # Get sell quote for slippage protection
            slippage_pct = float(action.get("slippage", 5))
            min_funds_wei = "0"
            estimated_funds = 0
            try:
                quote = await cli.quote_sell(token_address, amount_wei)
                if not isinstance(quote, dict):
                    quote = {}
                estimated_funds = int(quote.get("estimatedCost", 0) or quote.get("estimatedAmount", 0) or 0)
                if estimated_funds > 0:
                    min_funds_wei = str(int(estimated_funds * (1 - slippage_pct / 100)))
            except Exception as e:
                print(f"[Executor] Sell quote failed, proceeding without slippage protection: {e}")

            result = await cli.sell(token_address, amount_wei, min_funds_wei)
            tx_hash = result.get("txHash", result.get("hash", ""))

            # Compute exit values from quote
            exit_amount_bnb = estimated_funds / 10**18 if estimated_funds > 0 else 0
            exit_price = exit_amount_bnb / token_amount if token_amount > 0 else 0
            pnl = exit_amount_bnb - entry_amount

            # Close the position
            if position_id:
                await db.execute(
                    """UPDATE positions SET status = 'closed', exit_price = ?, exit_amount_bnb = ?,
                       pnl_bnb = ?, closed_at = ? WHERE id = ?""",
                    (exit_price, exit_amount_bnb, round(pnl, 8), now, position_id),
                )

            # Record the sell trade
            await db.execute(
                """INSERT INTO trades (position_id, token_address, side, amount_bnb,
                   token_quantity, price, tx_hash, slippage, approval_mode, executed_at)
                   VALUES (?, ?, 'sell', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    position_id,
                    token_address,
                    exit_amount_bnb,
                    token_amount,
                    exit_price,
                    tx_hash,
                    slippage_pct,
                    action.get("persona", ""),
                    now,
                ),
            )

            # Log activity
            await db.execute(
                "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
                ("trade_executed", token_address, json.dumps({
                    "side": "sell", "amount_bnb": round(exit_amount_bnb, 8),
                    "tx_hash": tx_hash, "pnl_bnb": round(pnl, 8),
                }), now),
            )
            await db.commit()

            # Feed the close outcome back into the creator reputation cache.
            # Best-effort — a failure here must not unwind the trade.
            try:
                cursor = await db.execute(
                    "SELECT creator_address, risk_score FROM tokens WHERE address = ?",
                    (token_address,),
                )
                row = await cursor.fetchone()
                row_dict = dict(row) if row else {}
                creator = row_dict.get("creator_address") or ""
                entry_grade = row_dict.get("risk_score") or ""
                if creator:
                    from services.creator_reputation import record_close
                    await record_close(creator, round(pnl, 8))
                # Signal outcome: compute pnl_pct from entry amount and record.
                pnl_pct = (pnl / entry_amount * 100) if entry_amount else None
                from services.signal_outcomes import record_trade_close
                await record_trade_close(token_address, entry_grade, pnl_pct, now)
            except Exception as e:
                print(f"[Executor] outcome update failed: {e}")

            # Broadcast trade_executed
            if ws_manager:
                await ws_manager.broadcast("trade_executed", {
                    "token_address": token_address,
                    "token_name": token_name,
                    "side": "sell",
                    "tx_hash": tx_hash,
                    "position_id": position_id,
                    "exit_amount_bnb": round(exit_amount_bnb, 8),
                    "pnl_bnb": round(pnl, 8),
                })

            return {"status": "executed", "tx_hash": tx_hash, "position_id": position_id, "pnl_bnb": round(pnl, 8)}

        return {"status": "error", "message": f"Unknown action type: {action_type}"}
    except Exception as e:
        print(f"[Executor] Error executing {action.get('action_type')} for {action.get('token_address')}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        await db.close()
