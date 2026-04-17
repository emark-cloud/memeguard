"""What I Avoided — background job that tracks prices of red-flagged tokens
to prove the agent's risk scoring was correct.

Checks prices at ~1h, ~6h, ~24h after flagging.
Detects confirmed rugs (price drop > 90% or liquidity pulled).
Calculates estimated savings based on persona trade amounts.
"""

import asyncio
from datetime import datetime, timezone

from database import get_db
from clients.bsc_web3 import BSCWeb3Client


async def start_avoided_tracker(ws_manager, interval: int = 300):
    """Periodically check prices of avoided tokens. Runs every 5 minutes."""
    web3 = BSCWeb3Client()

    try:
        while True:
            try:
                await check_avoided_tokens(web3, ws_manager)
            except Exception as e:
                print(f"[AvoidedTracker] Error: {e}")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass


async def check_avoided_tokens(web3: BSCWeb3Client, ws_manager):
    """Check price updates for all avoided tokens that still need tracking."""
    db = await get_db()
    try:
        # Get tokens that still need price checks (missing 1h, 6h, or 24h data)
        cursor = await db.execute(
            """SELECT * FROM avoided
               WHERE price_1h_later IS NULL
                  OR price_6h_later IS NULL
                  OR price_24h_later IS NULL
               ORDER BY flagged_at DESC
               LIMIT 20"""
        )
        tokens = [dict(row) for row in await cursor.fetchall()]

        if not tokens:
            return

        now = datetime.now(timezone.utc)

        for token in tokens:
            try:
                await _check_token_price(db, web3, ws_manager, token, now)
            except Exception as e:
                print(f"[AvoidedTracker] Error checking {token['token_address']}: {e}")

        await db.commit()
    finally:
        await db.close()


async def _check_token_price(db, web3, ws_manager, token: dict, now: datetime):
    """Check and update price for a single avoided token at the right interval."""
    flagged_at = token.get("flagged_at", "")
    if not flagged_at:
        return

    try:
        flagged_dt = datetime.fromisoformat(flagged_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return

    age_minutes = (now - flagged_dt).total_seconds() / 60

    # Determine which price slot to fill by matching the *current* age bucket,
    # not "first empty slot". If the backend was down for 24h, a token with
    # age_minutes=1500 and all slots NULL would otherwise fill 1h with a
    # 24h-old price, poisoning the signal.
    slot = None
    if age_minutes >= 1440 and token["price_24h_later"] is None:
        slot = "price_24h_later"
    elif 360 <= age_minutes < 1440 and token["price_6h_later"] is None:
        slot = "price_6h_later"
    elif 60 <= age_minutes < 360 and token["price_1h_later"] is None:
        slot = "price_1h_later"
    if slot is None:
        return  # Not time yet, already filled, or the window was missed

    # Get current price from on-chain
    info = await asyncio.to_thread(web3.get_token_info, token["token_address"])
    if not info:
        return

    last_price = info.get("lastPrice", 0)
    current_price = last_price / 10**18 if last_price else 0

    # Update the price slot
    await db.execute(
        f"UPDATE avoided SET {slot} = ? WHERE id = ?",
        (current_price, token["id"]),
    )

    # Check for confirmed rug
    price_at_flag = token.get("price_at_flag", 0) or 0
    is_rug = False

    if price_at_flag > 0 and current_price > 0:
        price_change_pct = ((current_price - price_at_flag) / price_at_flag) * 100
        # Confirmed rug: price dropped > 90%
        if price_change_pct <= -90:
            is_rug = True
    elif price_at_flag > 0 and current_price == 0:
        # Price is zero — definitely rugged
        is_rug = True

    # Also check if liquidity was pulled (graduated then emptied)
    liquidity_added = info.get("liquidityAdded", False)
    funds = info.get("funds", 0)
    if liquidity_added and funds == 0:
        is_rug = True

    if is_rug and not token.get("confirmed_rug"):
        await db.execute(
            "UPDATE avoided SET confirmed_rug = 1 WHERE id = ?",
            (token["id"],),
        )

        # Calculate estimated savings (what the user would have lost)
        estimated_savings = token.get("estimated_savings_bnb", 0.05)
        if price_at_flag > 0 and current_price >= 0:
            loss_pct = min(1.0, max(0, (price_at_flag - current_price) / price_at_flag))
            estimated_savings = round(estimated_savings * loss_pct, 6)
            await db.execute(
                "UPDATE avoided SET estimated_savings_bnb = ? WHERE id = ?",
                (estimated_savings, token["id"]),
            )

        # Log activity
        await db.execute(
            "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
            (
                "avoided_confirmed",
                token["token_address"],
                f"Confirmed rug: {token.get('token_name', 'Unknown')} — saved ~{estimated_savings:.4f} BNB",
                now.isoformat(),
            ),
        )

        # Broadcast avoided update
        if ws_manager:
            await ws_manager.broadcast("avoided_update", {
                "token_address": token["token_address"],
                "token_name": token.get("token_name", "Unknown"),
                "confirmed_rug": True,
                "estimated_savings_bnb": estimated_savings,
                "price_at_flag": price_at_flag,
                "current_price": current_price,
            })

            print(f"[AvoidedTracker] Confirmed rug: {token.get('token_name', '')} ({token['token_address'][:10]}...)")
