"""Interactive AI chat advisor — context-aware conversational interface.

Users can ask questions about tokens, compare risks, get explanations.
The chat is context-aware: pulls token data, positions, persona config into prompts.
"""

import asyncio
import json
import time
from datetime import datetime, timezone

from database import get_db, get_all_config
from services.llm_service import get_llm_service


# Recent history window pulled into each prompt (3 user/assistant turns).
RECENT_HISTORY_TURNS = 3

# TTL cache for the rarely-changing config slice of chat context.
# Persona and budget caps change on Settings saves, not per-message — refetching
# every turn is wasted IO and wasted prompt tokens.
_CONFIG_CTX_TTL_S = 60
_config_ctx_cache: tuple[float, list[str]] | None = None


async def _get_config_ctx_lines() -> list[str]:
    global _config_ctx_cache
    now = time.time()
    if _config_ctx_cache and (now - _config_ctx_cache[0]) < _CONFIG_CTX_TTL_S:
        return _config_ctx_cache[1]
    config = await get_all_config()
    lines = [
        f"Active persona: {config.get('persona', 'momentum')}",
        f"Budget: {config.get('max_per_trade_bnb', '0.05')} BNB/trade, {config.get('max_per_day_bnb', '0.3')} BNB/day",
        f"Max active positions: {config.get('max_active_positions', '3')}",
    ]
    _config_ctx_cache = (now, lines)
    return lines


async def _build_context(token_address: str | None = None) -> str:
    """Build context string with relevant data for the AI advisor."""
    parts = list(await _get_config_ctx_lines())

    db = await get_db()
    try:
        # Active positions summary (always fresh — changes on trades)
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM positions WHERE status = 'active'")
        pos_count = (await cursor.fetchone())["cnt"]
        parts.append(f"Active positions now: {pos_count}")

        # If asking about a specific token, include its data
        if token_address:
            cursor = await db.execute("SELECT * FROM tokens WHERE address = ?", (token_address,))
            token = await cursor.fetchone()
            if token:
                token = dict(token)
                parts.append(f"\nToken: {token.get('name', '?')} (${token.get('symbol', '?')})")
                parts.append(f"Address: {token_address}")
                parts.append(f"Risk score: {token.get('risk_score', 'unscored')}")
                parts.append(f"Bonding curve: {(token.get('bonding_curve_progress', 0) or 0) * 100:.1f}%")
                parts.append(f"Graduated: {'Yes' if token.get('graduated') else 'No'}")

                if token.get("risk_detail"):
                    try:
                        signals = json.loads(token["risk_detail"])
                        parts.append("\nRisk signals:")
                        for name, data in signals.items():
                            parts.append(f"  - {name}: {data.get('score', '?')}/10 — {data.get('detail', '')}")
                    except json.JSONDecodeError:
                        pass

                if token.get("risk_rationale"):
                    parts.append(f"\nAI rationale: {token['risk_rationale']}")

                # Pending actions
                cursor = await db.execute(
                    "SELECT * FROM pending_actions WHERE token_address = ? AND status = 'pending' LIMIT 1",
                    (token_address,),
                )
                action = await cursor.fetchone()
                if action:
                    action = dict(action)
                    parts.append(f"\nPending action: {action['action_type']} {action.get('amount_bnb', 0)} BNB")

        # Recent avoided tokens for context
        cursor = await db.execute(
            "SELECT token_name, risk_score, risk_rationale FROM avoided ORDER BY flagged_at DESC LIMIT 3"
        )
        avoided = await cursor.fetchall()
        if avoided:
            parts.append("\nRecently avoided tokens:")
            for a in avoided:
                a = dict(a)
                parts.append(f"  - {a.get('token_name', '?')} ({a.get('risk_score', '?')}): {a.get('risk_rationale', '')[:80]}")

    finally:
        await db.close()

    return "\n".join(parts)


async def _load_recent_history(db, token_address: str | None, turns: int) -> list[dict]:
    """Return last `turns` user/assistant pairs for this scope, oldest first.

    `token_address IS NULL` scopes to global chat; a non-null value scopes to
    that specific token's OpportunityDetail chat. NULLs don't compare with =
    in SQL, so we pick the WHERE clause based on the scope.
    """
    limit = turns * 2
    if token_address is None:
        cursor = await db.execute(
            "SELECT role, content FROM chat_messages "
            "WHERE token_address IS NULL ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    else:
        cursor = await db.execute(
            "SELECT role, content FROM chat_messages "
            "WHERE token_address = ? ORDER BY id DESC LIMIT ?",
            (token_address, limit),
        )
    rows = await cursor.fetchall()
    return [dict(r) for r in reversed(rows)]


async def _append_history(db, token_address: str | None, role: str, content: str):
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO chat_messages (token_address, role, content, created_at) "
        "VALUES (?, ?, ?, ?)",
        (token_address, role, content, now),
    )


async def chat(message: str, token_address: str | None = None) -> str:
    """Process a chat message and return the AI advisor's response."""
    llm = get_llm_service()
    if not llm.client:
        return "AI advisor is unavailable — no Gemini API key configured. Set GEMINI_API_KEY in your .env file."

    context = await _build_context(token_address)

    # Load recent history for this scope (global vs. per-token).
    db = await get_db()
    try:
        recent = await _load_recent_history(db, token_address, RECENT_HISTORY_TURNS)
    finally:
        await db.close()

    history_text = ""
    if recent:
        history_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Advisor'}: {m['content']}"
            for m in recent
        )
        history_text = f"\nConversation history:\n{history_text}\n"

    prompt = f"""You are FourScout's AI Trading Advisor for Four.meme (BNB Chain memecoins).
You help users understand token risks, make trading decisions, and learn about memecoin patterns.

Current context:
{context}
{history_text}
User question: {message}

Guidelines:
- Be specific and reference actual data from the context
- If asked about a token, analyze its risk signals and explain correlations
- If asked to compare tokens, use data you have available
- Explain trading concepts simply but accurately
- Never give financial advice — frame as analysis and education
- Keep responses concise (3-5 sentences unless asked for detail)
- If you don't have data on something, say so clearly"""

    try:
        from google.genai import types
        response = await asyncio.to_thread(
            llm.client.models.generate_content,
            model=llm.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=1024,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        reply = response.text.strip()
    except Exception as e:
        print(f"[ChatService] Error: {e}")
        return "Sorry, I encountered an error processing your question. Please try again."

    # Persist both turns in a single short transaction so the next call sees
    # them. We write even when the LLM succeeds; on failure we already returned.
    db = await get_db()
    try:
        await _append_history(db, token_address, "user", message)
        await _append_history(db, token_address, "assistant", reply)
        await db.commit()
    finally:
        await db.close()

    return reply


async def clear_chat_history(token_address: str | None = None, scope: str = "current"):
    """Clear chat history.

    scope='current': clear just this scope (global OR a specific token).
    scope='all':     clear every scope. Used when the caller passes no
                     token_address and wants the whole store wiped.
    """
    db = await get_db()
    try:
        if scope == "all":
            await db.execute("DELETE FROM chat_messages")
        elif token_address is None:
            await db.execute("DELETE FROM chat_messages WHERE token_address IS NULL")
        else:
            await db.execute("DELETE FROM chat_messages WHERE token_address = ?", (token_address,))
        await db.commit()
    finally:
        await db.close()
