"""What I Avoided — background job that tracks prices of red-flagged tokens
to prove the agent's risk scoring was correct.

Checks each token once at ~24h after flagging (stored in the
`price_24h_later` column).
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
        # Get tokens that still need the 24h price check. Oldest-first so rows
        # that are actually past 24h get filled before the newest flags that
        # aren't due yet.
        cursor = await db.execute(
            """SELECT * FROM avoided
               WHERE price_24h_later IS NULL
               ORDER BY flagged_at ASC
               LIMIT 20"""
        )
        tokens = [dict(row) for row in await cursor.fetchall()]

        if not tokens:
            return

        now = datetime.now(timezone.utc)

        for token in tokens:
            try:
                await _check_token_price(db, web3, ws_manager, token, now)
                # Commit per token so each on-chain call isn't held inside a
                # single long write transaction. The full loop can take 5–10s
                # of Web3 latency, which was long enough to exceed the 5s
                # busy_timeout on config writes and 500 the /config/bulk
                # endpoint from the Settings UI.
                await db.commit()
            except Exception as e:
                print(f"[AvoidedTracker] Error checking {token['token_address']}: {e}")
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

    # Single 24h check.
    if age_minutes < 1440 or token["price_24h_later"] is not None:
        return
    slot = "price_24h_later"

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
    price_change_pct_val = None

    if price_at_flag > 0 and current_price > 0:
        price_change_pct_val = ((current_price - price_at_flag) / price_at_flag) * 100
        # Confirmed rug: price dropped > 90%
        if price_change_pct_val <= -90:
            is_rug = True
    elif price_at_flag > 0 and current_price == 0:
        # Price is zero — definitely rugged
        is_rug = True
        price_change_pct_val = -100.0

    # Also check if liquidity was pulled (graduated then emptied)
    liquidity_added = info.get("liquidityAdded", False)
    funds = info.get("funds", 0) or 0
    if liquidity_added and funds == 0:
        is_rug = True

    if is_rug and not token.get("confirmed_rug"):
        await db.execute(
            "UPDATE avoided SET confirmed_rug = 1 WHERE id = ?",
            (token["id"],),
        )

        # Record the rug against the creator's reputation so repeat offenders
        # score worse on future scans. Best-effort — wrapping the whole block
        # in try/except keeps the avoided-tracker cycle resilient.
        try:
            cursor = await db.execute(
                "SELECT creator_address FROM tokens WHERE address = ?",
                (token["token_address"],),
            )
            creator_row = await cursor.fetchone()
            creator = (dict(creator_row).get("creator_address") or "") if creator_row else ""
            if creator:
                from services.creator_reputation import record_rug
                await record_rug(creator)
        except Exception as e:
            print(f"[AvoidedTracker] creator rug update failed: {e}")

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

    # Record a signal_outcomes row regardless of rug confirmation so we
    # capture "flagged but survived" datapoints too.
    try:
        from services.signal_outcomes import record_avoided_24h
        await record_avoided_24h(
            token["token_address"],
            token.get("risk_score", "") or "",
            price_change_pct_val,
            is_rug,
            now.isoformat(),
        )
    except Exception as e:
        print(f"[AvoidedTracker] signal_outcomes write failed: {e}")
