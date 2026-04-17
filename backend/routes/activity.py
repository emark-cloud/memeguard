"""Activity feed and override stats endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from database import get_db

router = APIRouter(tags=["activity"])


@router.get("/activity")
async def list_activity(
    event_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get chronological activity feed."""
    db = await get_db()
    try:
        query = "SELECT * FROM activity"
        params = []

        if event_type:
            query += " WHERE event_type = ?"
            params.append(event_type)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


@router.get("/overrides/stats")
async def override_stats():
    """Get behavioral nudge stats — how often the user overrode the agent."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) as total FROM overrides")
        total = (await cursor.fetchone())["total"]

        # User approved despite agent saying skip (red/amber)
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM overrides WHERE user_action = 'approved'"
        )
        approved_risky = (await cursor.fetchone())["cnt"]

        # User rejected agent's green buy recommendation
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM overrides WHERE user_action = 'rejected'"
        )
        rejected_safe = (await cursor.fetchone())["cnt"]

        # How many overridden approvals turned out bad (token rugged or large loss)
        cursor = await db.execute(
            """SELECT COUNT(*) as cnt FROM overrides o
               JOIN avoided a ON o.token_address = a.token_address
               WHERE o.user_action = 'approved' AND a.confirmed_rug = 1"""
        )
        overrides_rugged = (await cursor.fetchone())["cnt"]

        return {
            "total_overrides": total,
            "approved_risky": approved_risky,
            "rejected_safe": rejected_safe,
            "overrides_rugged": overrides_rugged,
        }
    finally:
        await db.close()


@router.get("/overrides/rejection_reasons")
async def rejection_reasons(days: int = Query(7, ge=1, le=90), limit: int = Query(3, ge=1, le=20)):
    """Return the most common user-supplied rejection reasons in the last N days.

    Reasons are free-text, so we collapse on exact-match trimmed strings. Good
    enough for a "top 3 last week" nudge — not trying to cluster semantics.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT rejection_reason AS reason, COUNT(*) AS cnt
               FROM pending_actions
               WHERE status = 'rejected'
                 AND rejection_reason IS NOT NULL
                 AND TRIM(rejection_reason) != ''
                 AND resolved_at >= ?
               GROUP BY TRIM(rejection_reason)
               ORDER BY cnt DESC
               LIMIT ?""",
            (since, limit),
        )
        rows = await cursor.fetchall()
        return {
            "window_days": days,
            "top": [{"reason": r["reason"], "count": r["cnt"]} for r in rows],
        }
    finally:
        await db.close()
