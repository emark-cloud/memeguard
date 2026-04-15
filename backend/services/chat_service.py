"""Interactive AI chat advisor — context-aware conversational interface.

Users can ask questions about tokens, compare risks, get explanations.
The chat is context-aware: pulls token data, positions, persona config into prompts.
"""

import json
from database import get_db, get_all_config
from services.llm_service import get_llm_service


# Session message history (in-memory, resets on restart)
_chat_history: list[dict] = []
MAX_HISTORY = 20


async def _build_context(token_address: str | None = None) -> str:
    """Build context string with relevant data for the AI advisor."""
    parts = []

    # Persona and config
    config = await get_all_config()
    persona = config.get("persona", "momentum")
    parts.append(f"Active persona: {persona}")
    parts.append(f"Budget: {config.get('max_per_trade_bnb', '0.05')} BNB/trade, {config.get('max_per_day_bnb', '0.3')} BNB/day")

    db = await get_db()
    try:
        # Active positions summary
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM positions WHERE status = 'active'")
        pos_count = (await cursor.fetchone())["cnt"]
        parts.append(f"Active positions: {pos_count}/{config.get('max_active_positions', '3')}")

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


async def chat(message: str, token_address: str | None = None) -> str:
    """Process a chat message and return the AI advisor's response."""
    global _chat_history

    llm = get_llm_service()
    if not llm.client:
        return "AI advisor is unavailable — no Gemini API key configured. Set GEMINI_API_KEY in your .env file."

    context = await _build_context(token_address)

    # Build conversation with history
    history_text = ""
    if _chat_history:
        recent = _chat_history[-10:]  # last 10 messages
        history_text = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Advisor'}: {m['content']}"
            for m in recent
        )
        history_text = f"\nConversation history:\n{history_text}\n"

    prompt = f"""You are MemeGuard's AI Trading Advisor for Four.meme (BNB Chain memecoins).
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
        response = llm.client.models.generate_content(
            model=llm.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=500,
            ),
        )
        reply = response.text.strip()

        # Update history
        _chat_history.append({"role": "user", "content": message})
        _chat_history.append({"role": "assistant", "content": reply})
        if len(_chat_history) > MAX_HISTORY * 2:
            _chat_history = _chat_history[-MAX_HISTORY * 2:]

        return reply
    except Exception as e:
        print(f"[ChatService] Error: {e}")
        return f"Sorry, I encountered an error processing your question. Please try again."


def clear_chat_history():
    """Clear the conversation history."""
    global _chat_history
    _chat_history = []
