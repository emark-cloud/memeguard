"""Trade executor — executes approved actions via Four.meme CLI."""

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

        if action_type == "buy":
            # Convert BNB to Wei
            funds_wei = str(int(amount_bnb * 10**18))

            # Get quote to compute min amount with slippage protection
            slippage_pct = float(action.get("slippage", 5))
            min_amount_wei = "0"
            estimated_tokens = 0
            try:
                quote = await cli.quote_buy(token_address, "0", funds_wei)
                estimated_tokens = int(quote.get("estimatedAmount", 0) or quote.get("amount", 0) or 0)
                if estimated_tokens > 0:
                    min_amount_wei = str(int(estimated_tokens * (1 - slippage_pct / 100)))
            except Exception as e:
                print(f"[Executor] Quote failed, proceeding without slippage protection: {e}")

            result = await cli.buy_by_funds(token_address, funds_wei, min_amount_wei)

            tx_hash = result.get("txHash", result.get("hash", ""))

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
                    "side": "buy",
                    "amount_bnb": amount_bnb,
                    "tx_hash": tx_hash,
                    "position_id": position_id,
                })

            return {"status": "executed", "tx_hash": tx_hash, "position_id": position_id}

        elif action_type == "sell":
            token_amount = action.get("tx_preview", "{}")
            if isinstance(token_amount, str):
                try:
                    preview = json.loads(token_amount)
                    token_amount = preview.get("token_amount", "0")
                except json.JSONDecodeError:
                    token_amount = "0"

            amount_wei = str(int(float(token_amount) * 10**18))
            result = await cli.sell(token_address, amount_wei)

            tx_hash = result.get("txHash", result.get("hash", ""))

            await db.execute(
                "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
                ("trade_executed", token_address, json.dumps({"side": "sell", "tx_hash": tx_hash}), now),
            )
            await db.commit()

            # Broadcast trade_executed
            if ws_manager:
                await ws_manager.broadcast("trade_executed", {
                    "token_address": token_address,
                    "side": "sell",
                    "tx_hash": tx_hash,
                })

            return {"status": "executed", "tx_hash": tx_hash}

        return {"status": "error", "message": f"Unknown action type: {action_type}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await db.close()
