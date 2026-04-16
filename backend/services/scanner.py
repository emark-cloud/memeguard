"""Token scanner — discovers new Four.meme launches and queues them for risk scoring."""

import asyncio
import json
from datetime import datetime, timezone

from config import settings
from database import get_db


async def start_scanner(ws_manager):
    """Main scanner loop. Polls Four.meme for new tokens at configured interval."""
    from clients.fourmeme_api import FourMemeAPI

    api = FourMemeAPI()

    try:
        while True:
            try:
                await scan_new_tokens(api, ws_manager)
            except Exception as e:
                print(f"[Scanner] Error: {e}")
            await asyncio.sleep(settings.scan_interval_seconds)
    finally:
        await api.close()


async def scan_new_tokens(api, ws_manager):
    """Fetch new tokens from Four.meme and store any we haven't seen."""
    try:
        tokens = await api.search_tokens(page=1, size=20)
    except Exception as e:
        print(f"[Scanner] API error: {e}")
        return

    if not tokens:
        return

    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        new_count = 0

        for token in tokens:
            # Four.meme API uses tokenAddress, userAddress, createDate
            address = token.get("tokenAddress", "") or token.get("address", "")
            if not address:
                continue

            # Check if we already have this token
            cursor = await db.execute(
                "SELECT address FROM tokens WHERE address = ?", (address,)
            )
            existing = await cursor.fetchone()
            if existing:
                continue

            # Convert createDate (ms timestamp string) to ISO string
            create_date = token.get("createDate", 0)
            launch_time = ""
            if create_date:
                try:
                    ts_ms = int(create_date)
                    launch_time = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
                except (ValueError, TypeError, OSError):
                    launch_time = str(create_date)

            try:
                progress = float(token.get("progress", 0) or 0)
            except (ValueError, TypeError):
                progress = 0.0
            # Progress from API is 0-100, store as 0-1 float
            if progress > 1:
                progress = progress / 100.0

            # New token — store it
            await db.execute(
                """INSERT INTO tokens (address, name, symbol, creator_address, launch_time,
                   bonding_curve_progress, graduated, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    address,
                    token.get("name", ""),
                    token.get("shortName", "") or token.get("symbol", ""),
                    token.get("userAddress", "") or token.get("creator", ""),
                    launch_time,
                    progress,
                    1 if token.get("status") == "GRADUATED" else 0,
                    now,
                ),
            )

            # Log activity
            await db.execute(
                "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
                ("new_token", address, json.dumps({"name": token.get("name", ""), "symbol": token.get("shortName", "")}), now),
            )

            new_count += 1

            # Broadcast to WebSocket clients
            await ws_manager.broadcast("new_token", {
                "address": address,
                "name": token.get("name", ""),
                "symbol": token.get("shortName", ""),
                "progress": progress,
            })

        if new_count > 0:
            await db.commit()
            print(f"[Scanner] Found {new_count} new tokens")

        # Queue risk scoring for tokens without scores
        cursor = await db.execute(
            "SELECT address FROM tokens WHERE risk_score IS NULL ORDER BY created_at DESC LIMIT 10"
        )
        unscored = await cursor.fetchall()
        if unscored:
            from services.risk_engine import score_token

            # Cap parallel scorers: too much concurrency causes SQLite write
            # contention (busy_timeout expiry) and bursts Gemini's per-minute
            # quota. Three is enough to overlap LLM wait time with signal IO.
            sem = asyncio.Semaphore(3)

            async def _safe_score(addr):
                async with sem:
                    try:
                        await score_token(addr, ws_manager)
                    except Exception as e:
                        print(f"[Scanner] Scoring error for {addr}: {e}")

            await asyncio.gather(*[_safe_score(row["address"]) for row in unscored])

    finally:
        await db.close()
