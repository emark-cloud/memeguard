"""Risk scoring engine — 8 deterministic signals aggregated into GREEN/AMBER/RED.

AI (LLM) is NOT used for scoring. Only for generating the plain-language rationale after.
"""

import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from database import get_db, get_all_config
from clients.bsc_web3 import BSCWeb3Client
from clients.market_api import MarketContext


@dataclass
class SignalResult:
    name: str
    score: float  # 0-10
    weight: int  # 1=LOW, 2=MEDIUM, 3=HIGH
    detail: str


@dataclass
class RiskScore:
    grade: str  # green / amber / red
    percentage: float
    signals: list  # list of SignalResult dicts
    primary_risk: str


# Singleton clients (initialized lazily)
_web3_client: BSCWeb3Client | None = None
_market_client: MarketContext | None = None


def _get_web3() -> BSCWeb3Client:
    global _web3_client
    if _web3_client is None:
        _web3_client = BSCWeb3Client()
    return _web3_client


def _get_market() -> MarketContext:
    global _market_client
    if _market_client is None:
        _market_client = MarketContext()
    return _market_client


# ──────────────────────────────────────────
# Signal 1: Creator History (HIGH weight=3)
# ──────────────────────────────────────────
def score_creator_history(creator_address: str) -> SignalResult:
    """Check if creator has launched tokens before and their outcomes."""
    if not creator_address:
        return SignalResult("creator_history", 5, 3, "No creator address available")

    web3 = _get_web3()
    history = web3.get_creator_history(creator_address)

    if not history:
        return SignalResult("creator_history", 7, 3, "First-time creator — no prior launches found")

    count = len(history)
    if count >= 4:
        return SignalResult("creator_history", 1, 3, f"Serial launcher: {count} tokens in recent history — high rug risk")
    if count >= 2:
        return SignalResult("creator_history", 4, 3, f"Creator has {count} prior tokens — moderate concern")

    return SignalResult("creator_history", 8, 3, f"Creator has {count} prior token(s)")


# ──────────────────────────────────────────
# Signal 2: Holder Concentration (HIGH weight=3)
# ──────────────────────────────────────────
def score_holder_concentration(token_address: str) -> SignalResult:
    """Check if token supply is concentrated in few wallets."""
    web3 = _get_web3()
    data = web3.get_holder_balances(token_address)

    max_single = data.get("max_single_pct", 0)
    top5 = data.get("top5_pct", 0)
    holders = data.get("unique_holders", 0)

    if max_single > 20:
        return SignalResult("holder_concentration", 1, 3, f"Single wallet holds {max_single}% — extreme concentration")
    if top5 > 40:
        return SignalResult("holder_concentration", 3, 3, f"Top 5 wallets hold {top5}% of supply")
    if top5 > 20:
        return SignalResult("holder_concentration", 6, 3, f"Top 5 wallets hold {top5}% — moderate concentration")
    if holders < 5:
        return SignalResult("holder_concentration", 4, 3, f"Only {holders} unique holders found")

    return SignalResult("holder_concentration", 9, 3, f"Healthy distribution: top 5 hold {top5}%, {holders} holders")


# ──────────────────────────────────────────
# Signal 3: Liquidity Depth & Age (MEDIUM weight=2)
# ──────────────────────────────────────────
def score_liquidity(token_address: str, bnb_price_usd: float = 600) -> SignalResult:
    """Check liquidity depth and token age."""
    web3 = _get_web3()
    info = web3.get_token_info(token_address)

    if not info:
        return SignalResult("liquidity", 3, 2, "Could not fetch token info")

    funds_wei = info.get("funds", 0)
    max_funds_wei = info.get("maxFunds", 0)
    liquidity_added = info.get("liquidityAdded", False)
    launch_time = info.get("launchTime", 0)

    funds_bnb = funds_wei / 10**18 if funds_wei else 0
    liquidity_usd = funds_bnb * bnb_price_usd

    # Check token age
    age_minutes = 0
    if launch_time:
        age_seconds = int(datetime.now(timezone.utc).timestamp()) - launch_time
        age_minutes = age_seconds / 60

    if liquidity_added:
        if liquidity_usd > 5000:
            return SignalResult("liquidity", 9, 2, f"Graduated. Liquidity: ${liquidity_usd:.0f}")
        return SignalResult("liquidity", 7, 2, f"Graduated. Liquidity: ${liquidity_usd:.0f}")

    if liquidity_usd < 500:
        return SignalResult("liquidity", 2, 2, f"Low liquidity: ${liquidity_usd:.0f} — hard to exit")

    if age_minutes < 5:
        return SignalResult("liquidity", 4, 2, f"Very new ({age_minutes:.0f}m old), ${liquidity_usd:.0f} liquidity")

    progress = (funds_wei / max_funds_wei * 100) if max_funds_wei else 0
    return SignalResult("liquidity", 6, 2, f"Bonding curve {progress:.0f}% full, ${liquidity_usd:.0f} liquidity")


# ──────────────────────────────────────────
# Signal 4: Bonding Curve Velocity (HIGH weight=3)
# ──────────────────────────────────────────
def score_bonding_velocity(token_address: str) -> SignalResult:
    """Check if bonding curve is filling unusually fast (bot activity)."""
    web3 = _get_web3()
    info = web3.get_token_info(token_address)

    if not info:
        return SignalResult("bonding_velocity", 5, 3, "Could not fetch token info")

    funds_wei = info.get("funds", 0)
    launch_time = info.get("launchTime", 0)
    liquidity_added = info.get("liquidityAdded", False)

    if liquidity_added:
        return SignalResult("bonding_velocity", 7, 3, "Already graduated — velocity N/A")

    if not launch_time:
        return SignalResult("bonding_velocity", 5, 3, "No launch time available")

    age_seconds = int(datetime.now(timezone.utc).timestamp()) - launch_time
    if age_seconds <= 0:
        return SignalResult("bonding_velocity", 5, 3, "Token not yet launched")

    funds_bnb = funds_wei / 10**18 if funds_wei else 0
    # Rate: BNB raised per minute
    rate_per_min = (funds_bnb / age_seconds) * 60

    # Average Four.meme token raises ~18 BNB over hours/days
    # Anything above 1 BNB/min in first 10 minutes is suspicious
    age_minutes = age_seconds / 60

    if age_minutes < 10 and rate_per_min > 2:
        return SignalResult("bonding_velocity", 1, 3, f"Extremely fast fill: {rate_per_min:.2f} BNB/min — likely coordinated buying")
    if age_minutes < 10 and rate_per_min > 0.5:
        return SignalResult("bonding_velocity", 4, 3, f"Fast fill: {rate_per_min:.2f} BNB/min in first {age_minutes:.0f}m")
    if rate_per_min > 1:
        return SignalResult("bonding_velocity", 5, 3, f"Above average velocity: {rate_per_min:.2f} BNB/min")

    return SignalResult("bonding_velocity", 8, 3, f"Normal velocity: {rate_per_min:.3f} BNB/min over {age_minutes:.0f}m")


# ──────────────────────────────────────────
# Signal 5: Tax Token Flags (MEDIUM weight=2)
# ──────────────────────────────────────────
def score_tax_token(token_address: str) -> SignalResult:
    """Check for tax token flags and fee parameters."""
    web3 = _get_web3()
    tax = web3.is_tax_token(token_address)

    if not tax.get("is_tax"):
        return SignalResult("tax_token", 10, 2, "Not a tax token — no on-chain fees")

    fee_bps = tax.get("fee_rate_bps", 0)
    fee_pct = fee_bps / 100 if fee_bps else 0

    if fee_pct > 10:
        return SignalResult("tax_token", 0, 2, f"Extreme tax: {fee_pct}% per trade")
    if fee_pct > 5:
        return SignalResult("tax_token", 3, 2, f"High tax: {fee_pct}% per trade")
    if fee_pct > 3:
        return SignalResult("tax_token", 5, 2, f"Moderate tax: {fee_pct}% per trade")

    return SignalResult("tax_token", 8, 2, f"Low tax: {fee_pct}% per trade")


# ──────────────────────────────────────────
# Signal 6: Volume Consistency (MEDIUM weight=2)
# ──────────────────────────────────────────
def score_volume_consistency(token_address: str) -> SignalResult:
    """Placeholder — analyzes trade patterns for wash trading.

    Full implementation will use CLI events data.
    """
    # For Phase 1, return neutral score
    return SignalResult("volume_consistency", 5, 2, "Volume analysis pending — insufficient data")


# ──────────────────────────────────────────
# Signal 7: Social Signal (LOW weight=1)
# ──────────────────────────────────────────
def score_social_signal(token_data: dict) -> SignalResult:
    """Check social presence and description quality."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    description = token_data.get("description", "") or ""
    has_twitter = bool(token_data.get("twitter_url") or token_data.get("twitter"))
    has_telegram = bool(token_data.get("telegram_url") or token_data.get("telegram"))

    score = 5  # baseline

    if has_twitter:
        score += 1
    if has_telegram:
        score += 1

    # Check for pump language
    pump_words = ["1000x", "moon", "guaranteed", "easy money", "ape in", "next 100x"]
    desc_lower = description.lower()
    pump_count = sum(1 for w in pump_words if w in desc_lower)

    if pump_count >= 2:
        score -= 3
        detail = f"Pump language detected ({pump_count} flags)"
    elif pump_count == 1:
        score -= 1
        detail = "Minor pump language"
    else:
        detail = ""

    # VADER sentiment
    if description:
        analyzer = SentimentIntensityAnalyzer()
        sentiment = analyzer.polarity_scores(description)
        if sentiment["compound"] < -0.3:
            score -= 1
            detail += " Negative sentiment in description."
    else:
        detail += " No description provided."

    socials = []
    if has_twitter:
        socials.append("Twitter")
    if has_telegram:
        socials.append("Telegram")
    social_str = f"Socials: {', '.join(socials)}" if socials else "No socials linked"

    score = max(0, min(10, score))
    return SignalResult("social_signal", score, 1, f"{social_str}. {detail}".strip())


# ──────────────────────────────────────────
# Signal 8: Market Context (LOW weight=1)
# ──────────────────────────────────────────
async def score_market_context() -> SignalResult:
    """Check overall market conditions."""
    market = _get_market()
    try:
        fg = await market.get_fear_greed()
        bnb_change = await market.get_bnb_24h_change()
    except Exception:
        return SignalResult("market_context", 5, 1, "Market data unavailable")

    fg_value = fg.get("value", 50)
    fg_label = fg.get("classification", "Neutral")

    score = 5  # baseline

    if fg_value < 25:
        score -= 2  # extreme fear = raise bar
    elif fg_value < 40:
        score -= 1
    elif fg_value > 75:
        score += 1  # greed = easier entry

    if bnb_change < -5:
        score -= 1
    elif bnb_change > 5:
        score += 1

    score = max(0, min(10, score))
    return SignalResult(
        "market_context", score, 1,
        f"Fear & Greed: {fg_value} ({fg_label}). BNB 24h: {bnb_change:+.1f}%"
    )


# ──────────────────────────────────────────
# Aggregation
# ──────────────────────────────────────────
async def compute_risk_score(token_address: str, token_data: dict = None) -> RiskScore:
    """Run all signals and compute aggregate risk score."""
    if token_data is None:
        token_data = {}

    creator = token_data.get("creator_address", "") or token_data.get("creator", "")

    # Run deterministic signals
    signals = [
        score_creator_history(creator),
        score_holder_concentration(token_address),
        score_liquidity(token_address),
        score_bonding_velocity(token_address),
        score_tax_token(token_address),
        score_volume_consistency(token_address),
        score_social_signal(token_data),
    ]

    # Run async signal
    market_signal = await score_market_context()
    signals.append(market_signal)

    # Weighted aggregation
    weighted_sum = sum(s.score * s.weight for s in signals)
    max_possible = sum(10 * s.weight for s in signals)
    percentage = (weighted_sum / max_possible * 100) if max_possible > 0 else 0

    if percentage >= 65:
        grade = "green"
    elif percentage >= 40:
        grade = "amber"
    else:
        grade = "red"

    # Find primary risk factor (lowest weighted score)
    worst = min(signals, key=lambda s: s.score * s.weight)
    primary_risk = f"{worst.name}: {worst.detail}"

    return RiskScore(
        grade=grade,
        percentage=round(percentage, 1),
        signals=[asdict(s) for s in signals],
        primary_risk=primary_risk,
    )


async def score_token(token_address: str, ws_manager=None):
    """Score a token and persist results to the database."""
    db = await get_db()
    try:
        # Get token data from DB
        cursor = await db.execute("SELECT * FROM tokens WHERE address = ?", (token_address,))
        token_row = await cursor.fetchone()
        if not token_row:
            return

        token_data = dict(token_row)
        result = await compute_risk_score(token_address, token_data)
        now = datetime.now(timezone.utc).isoformat()

        # Generate LLM rationale
        risk_detail = {s["name"]: s for s in result.signals}
        rationale = result.primary_risk  # fallback
        escalation = None
        try:
            from services.llm_service import get_llm_service
            llm = get_llm_service()
            rationale = await llm.generate_rationale(token_data, risk_detail)

            # Escalation: deep AI analysis for AMBER tokens
            if result.grade == "amber":
                escalation = await llm.deep_analyze_amber(token_data, risk_detail)
                rationale += f"\n\n[Deep Analysis] {escalation.get('analysis', '')}"
        except Exception as e:
            print(f"[RiskEngine] LLM rationale error: {e}")

        # Update token with risk score
        await db.execute(
            """UPDATE tokens SET risk_score = ?, risk_detail = ?, risk_rationale = ?, last_checked = ?
               WHERE address = ?""",
            (result.grade, json.dumps(risk_detail), rationale, now, token_address),
        )

        # Log scan event
        await db.execute(
            "INSERT INTO scans (token_address, scan_type, risk_score, created_at) VALUES (?, ?, ?, ?)",
            (token_address, "risk_score", result.grade, now),
        )

        # Log activity
        await db.execute(
            "INSERT INTO activity (event_type, token_address, detail, created_at) VALUES (?, ?, ?, ?)",
            ("risk_scored", token_address, json.dumps({"grade": result.grade, "pct": result.percentage}), now),
        )

        # If red, add to avoided tracker
        if result.grade == "red":
            info = _get_web3().get_token_info(token_address)
            price = info.get("lastPrice", 0) / 10**18 if info.get("lastPrice") else 0
            await db.execute(
                """INSERT OR IGNORE INTO avoided (token_address, token_name, risk_score, risk_rationale,
                   price_at_flag, estimated_savings_bnb, flagged_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    token_address,
                    token_data.get("name", ""),
                    result.grade,
                    result.primary_risk,
                    price,
                    0.05,  # default persona amount as estimated savings
                    now,
                ),
            )

        await db.commit()

        # Broadcast to frontend
        if ws_manager:
            await ws_manager.broadcast("risk_scored", {
                "address": token_address,
                "grade": result.grade,
                "percentage": result.percentage,
                "primary_risk": result.primary_risk,
            })

            # Risk alert on grade change
            old_grade = token_data.get("risk_score")
            if old_grade and old_grade != result.grade:
                await ws_manager.broadcast("risk_alert", {
                    "address": token_address,
                    "old_grade": old_grade,
                    "new_grade": result.grade,
                    "reason": result.primary_risk,
                })

        # Auto-propose: persona decides → approval gate → pending action
        if result.grade != "red":
            try:
                await _auto_propose(db, token_address, token_data, result, rationale, ws_manager)
            except Exception as e:
                print(f"[RiskEngine] Auto-propose error: {e}")

    finally:
        await db.close()


async def _auto_propose(db, token_address, token_data, result, rationale, ws_manager):
    """Run persona engine and approval gate to auto-create pending actions."""
    from services.persona_engine import decide_action
    from services.approval_gate import check_approval

    # Get current position count and daily spend
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM positions WHERE status = 'active'")
    active_positions = (await cursor.fetchone())["cnt"]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cursor = await db.execute(
        "SELECT COALESCE(SUM(amount_bnb), 0) as spent FROM trades WHERE executed_at >= ?",
        (today,),
    )
    budget_used = (await cursor.fetchone())["spent"]

    action = await decide_action(
        risk_grade=result.grade,
        risk_percentage=result.percentage,
        token_data=token_data,
        active_positions=active_positions,
        budget_used_today=budget_used,
    )

    if action.action != "buy":
        return

    # Check approval gate
    gate_result = await check_approval(action.action, action.amount_bnb, result.grade)
    if gate_result == "blocked":
        return

    # Check for existing pending action on this token
    cursor = await db.execute(
        "SELECT id FROM pending_actions WHERE token_address = ? AND status = 'pending'",
        (token_address,),
    )
    if await cursor.fetchone():
        return

    now = datetime.now(timezone.utc).isoformat()

    # Build tx preview
    tx_preview = "{}"
    try:
        from services.tx_builder import build_buy_preview, preview_to_json
        preview = await build_buy_preview(token_address, action.amount_bnb, action.slippage)
        tx_preview = preview_to_json(preview)
    except Exception as e:
        print(f"[RiskEngine] TX preview error: {e}")

    config = await get_all_config()
    persona_name = config.get("persona", "momentum")

    await db.execute(
        """INSERT INTO pending_actions (token_address, action_type, amount_bnb, slippage,
           persona, risk_score, rationale, tx_preview, status, created_at)
           VALUES (?, 'buy', ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            token_address,
            action.amount_bnb,
            action.slippage,
            persona_name,
            result.grade,
            rationale,
            tx_preview,
            "auto" if gate_result == "auto" else "pending",
            now,
        ),
    )
    await db.commit()

    if gate_result == "auto":
        # Auto-execute
        cursor = await db.execute(
            "SELECT * FROM pending_actions WHERE token_address = ? AND status = 'auto' ORDER BY created_at DESC LIMIT 1",
            (token_address,),
        )
        pending = await cursor.fetchone()
        if pending:
            await db.execute(
                "UPDATE pending_actions SET status = 'approved', resolved_at = ? WHERE id = ?",
                (now, pending["id"]),
            )
            await db.commit()
            from services.executor import execute_approved_action
            await execute_approved_action(dict(pending))

    # Broadcast action_proposed
    if ws_manager:
        await ws_manager.broadcast("action_proposed", {
            "token_address": token_address,
            "action_type": "buy",
            "amount_bnb": action.amount_bnb,
            "risk_score": result.grade,
            "rationale": rationale,
        })
