"""Approval gate — determines whether a trade auto-executes or requires user approval.

Four modes:
  1. approve_each   — every trade needs explicit user approval
  2. approve_per_session — first trade requires approval, rest auto-execute within session
  3. budget_threshold — auto-execute under threshold amount, require approval above
  4. monitor_only   — no trades at all, recommendations only
"""

from database import get_all_config, get_db


# Track session approval state (resets on server restart)
_session_approved = False


async def check_approval(
    action_type: str,
    amount_bnb: float,
    risk_grade: str,
) -> str:
    """Check if a trade should auto-execute or require approval.

    Returns:
        "auto"    — proceed to execution immediately
        "pending" — create pending_action for user approval
        "blocked" — do not trade (monitor_only mode)
    """
    global _session_approved

    config = await get_all_config()
    mode = config.get("approval_mode", "approve_each")

    if mode == "monitor_only":
        return "blocked"

    if mode == "approve_each":
        return "pending"

    if mode == "approve_per_session":
        if _session_approved:
            return "auto"
        return "pending"

    if mode == "budget_threshold":
        threshold = float(config.get("max_per_trade_bnb", 0.05))
        if amount_bnb <= threshold * 0.5:
            return "auto"
        return "pending"

    return "pending"


def mark_session_approved():
    """Mark the session as approved (called after first manual approval)."""
    global _session_approved
    _session_approved = True


def reset_session():
    """Reset session approval state."""
    global _session_approved
    _session_approved = False
