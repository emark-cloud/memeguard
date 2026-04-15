"""LLM service for generating plain-language risk rationales.

Uses Google Gemini (free tier). Provider abstraction allows swapping to Anthropic later.
"""

from config import settings


class LLMService:
    """Generates natural language explanations for risk scores."""

    def __init__(self):
        self.provider = "gemini"
        self.client = None
        self.model = "gemini-2.0-flash"
        self._init_client()

    def _init_client(self):
        if not settings.gemini_api_key:
            print("[LLM] No GEMINI_API_KEY set — rationale generation disabled")
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=settings.gemini_api_key)
        except ImportError:
            print("[LLM] google-genai not installed")
        except Exception as e:
            print(f"[LLM] Init error: {e}")

    async def generate_rationale(self, token_data: dict, risk_signals: dict) -> str:
        """Generate a multi-signal narrative synthesis.

        Instead of one-line-per-signal, correlates signals to detect patterns
        like "serial launcher + high concentration = pump-and-dump".
        """
        if not self.client:
            return self._fallback_rationale(risk_signals)

        # Build signal summary for the prompt
        signal_lines = []
        for name, data in risk_signals.items():
            if isinstance(data, dict):
                signal_lines.append(f"- {name}: {data.get('score', '?')}/10 (weight {data.get('weight', 1)}) — {data.get('detail', 'N/A')}")

        token_name = token_data.get("name", "Unknown")
        token_symbol = token_data.get("symbol", "???")
        progress = token_data.get("bonding_curve_progress", 0)
        graduated = token_data.get("graduated", False)

        prompt = f"""You are a memecoin risk analyst for Four.meme on BNB Chain.
Analyze these risk signals for token {token_name} (${token_symbol}):

{chr(10).join(signal_lines)}

Token status: {'Graduated to PancakeSwap' if graduated else f'Bonding curve {(progress or 0) * 100:.0f}% filled'}

IMPORTANT: Don't just list each signal. Synthesize them into a narrative:
- Look for CORRELATED PATTERNS (e.g., "serial creator + high concentration = pump-and-dump setup",
  "fast bonding velocity + no socials = bot-driven launch", "graduated + healthy distribution = legitimate project")
- Lead with the overall assessment (safe / moderate risk / dangerous)
- Explain WHY the combination of signals matters, not just individual scores
- Be specific and actionable

Write 2-3 sentences, under 80 words. No disclaimers."""

        try:
            from google.genai import types
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=200,
                ),
            )
            return response.text.strip()
        except Exception as e:
            print(f"[LLM] Generation error: {e}")
            return self._fallback_rationale(risk_signals)

    async def deep_analyze_amber(self, token_data: dict, risk_signals: dict) -> dict:
        """Deep AI analysis for AMBER tokens — the escalation pipeline.

        Returns a dict with:
          - recommendation: "lean_buy" / "lean_skip" / "watch"
          - confidence: 0-100
          - analysis: detailed explanation
        """
        if not self.client:
            return {"recommendation": "watch", "confidence": 50, "analysis": "LLM unavailable for deep analysis"}

        signal_lines = []
        for name, data in risk_signals.items():
            if isinstance(data, dict):
                signal_lines.append(f"- {name}: {data.get('score', '?')}/10 — {data.get('detail', 'N/A')}")

        token_name = token_data.get("name", "Unknown")
        token_symbol = token_data.get("symbol", "???")
        description = token_data.get("description", "") or ""

        prompt = f"""You are a senior memecoin analyst. This AMBER-rated token needs deeper analysis.

Token: {token_name} (${token_symbol})
Description: {description[:300] or 'None provided'}

Risk signals:
{chr(10).join(signal_lines)}

This token scored AMBER (borderline). Analyze whether it leans toward BUY or SKIP:
1. Are the negative signals temporary (low liquidity on new token) or structural (serial launcher)?
2. Do the positive signals indicate genuine momentum or manufactured activity?
3. What's the risk/reward balance?

Respond in this exact format:
RECOMMENDATION: lean_buy OR lean_skip OR watch
CONFIDENCE: [0-100]
ANALYSIS: [2-3 sentences explaining your reasoning]"""

        try:
            from google.genai import types
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=300,
                ),
            )
            text = response.text.strip()

            # Parse structured response
            recommendation = "watch"
            confidence = 50
            analysis = text

            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("RECOMMENDATION:"):
                    rec = line.split(":", 1)[1].strip().lower()
                    if rec in ("lean_buy", "lean_skip", "watch"):
                        recommendation = rec
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                elif line.startswith("ANALYSIS:"):
                    analysis = line.split(":", 1)[1].strip()

            return {"recommendation": recommendation, "confidence": confidence, "analysis": analysis}
        except Exception as e:
            print(f"[LLM] Deep analysis error: {e}")
            return {"recommendation": "watch", "confidence": 50, "analysis": f"Analysis failed: {e}"}

    async def classify_description(self, description: str) -> str:
        """Classify a token description as legit/scam/hype."""
        if not self.client or not description:
            return "unknown"

        prompt = f"""Classify this memecoin description into one category: legit, scam, or hype.
Only respond with one word.

Description: {description[:500]}"""

        try:
            from google.genai import types
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=10),
            )
            result = response.text.strip().lower()
            if result in ("legit", "scam", "hype"):
                return result
            return "unknown"
        except Exception:
            return "unknown"

    def _fallback_rationale(self, risk_signals: dict) -> str:
        """Generate a basic rationale without LLM."""
        worst = None
        for name, data in risk_signals.items():
            if isinstance(data, dict):
                score = data.get("score", 5)
                weight = data.get("weight", 1)
                if worst is None or (score * weight) < (worst[1] * worst[2]):
                    worst = (name, score, weight, data.get("detail", ""))

        if worst:
            return f"Primary concern: {worst[0].replace('_', ' ')} — {worst[3]}"
        return "Risk assessment computed. Check individual signal scores for details."


# Singleton
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
