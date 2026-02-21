"""
Competitive Intelligence - LLM-Powered Deep Analysis

Uses OpenRouter (Gemini) to generate:
  1. Market positioning narrative
  2. Strategic pricing recommendations
  3. SWOT-style competitive assessment
  4. Actionable next steps

The LLM receives a structured summary of scraped competitor data,
NOT raw HTML. This keeps prompts small, focused, and cheap.

DESIGN:
- Reads OPENROUTER_API_KEY from environment / .env
- Falls back gracefully if API is unreachable or key is missing
- Returns a structured dict that maps to LLMAnalysis schema
- Temperature kept low (0.3) for factual, actionable output
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def _load_env():
    """Best-effort load of .env from project root."""
    try:
        from dotenv import load_dotenv
        # Walk up from this file to find .env
        here = os.path.dirname(os.path.abspath(__file__))
        for _ in range(5):
            env_path = os.path.join(here, ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path)
                return
            here = os.path.dirname(here)
    except ImportError:
        pass


_load_env()

# ── Config ────────────────────────────────────────────────────────

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "15"))


# ══════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════

def generate_llm_analysis(
    product_name: str,
    product_description: Optional[str],
    my_price: float,
    category: Optional[str],
    market_summary: Dict[str, Any],
    position: Dict[str, Any],
    competitors: List[Dict[str, Any]],
    rule_insights: List[str],
) -> Optional[Dict[str, Any]]:
    """
    Call OpenRouter LLM to produce a deep competitive analysis.

    Returns a dict with keys:
        executive_summary    – 2-3 sentence overview
        pricing_strategy     – recommended pricing actions
        strengths            – list of competitive strengths
        weaknesses           – list of competitive weaknesses
        opportunities        – market opportunities
        threats              – competitive threats
        recommended_price    – suggested optimal price (float or null)
        action_items         – prioritised next steps (list of strings)
        market_analysis      – paragraph-length deep dive

    Returns None if:
        - API key is missing
        - Network / API error
        - Response is unparseable
    """
    if not OPENROUTER_API_KEY:
        logger.warning("LLM analysis skipped: OPENROUTER_API_KEY not set")
        return None

    prompt = _build_prompt(
        product_name, product_description, my_price, category,
        market_summary, position, competitors, rule_insights,
    )

    try:
        import requests

        payload = {
            "model": OPENROUTER_MODEL,
            "temperature": 0.3,
            "max_tokens": 1200,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior business analyst specialising in e-commerce competitive intelligence. "
                        "Respond ONLY with valid JSON (no markdown, no code fences). "
                        "Be data-driven, concise, and actionable."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://trademind.app",
            "X-Title": "TradeMind Competitive Intelligence",
        }

        resp = requests.post(
            OPENROUTER_URL,
            json=payload,
            headers=headers,
            timeout=LLM_TIMEOUT,
        )

        if resp.status_code != 200:
            logger.error(f"OpenRouter returned {resp.status_code}: {resp.text[:300]}")
            return None

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Strip markdown code fences if the model wraps them anyway
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        if content.startswith("json"):
            content = content[4:].strip()

        analysis = json.loads(content)
        logger.info("LLM analysis generated successfully")
        return _normalise_analysis(analysis)

    except json.JSONDecodeError as e:
        logger.error(f"LLM response not valid JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"LLM analysis failed: {type(e).__name__}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
#  Prompt Builder
# ══════════════════════════════════════════════════════════════════

def _build_prompt(
    product_name: str,
    product_description: Optional[str],
    my_price: float,
    category: Optional[str],
    market_summary: Dict[str, Any],
    position: Dict[str, Any],
    competitors: List[Dict[str, Any]],
    rule_insights: List[str],
) -> str:
    """Build a tightly-structured prompt with all scraped context."""

    comp_lines = []
    for i, c in enumerate(competitors[:10], 1):
        line = f"  {i}. {c.get('title', 'N/A')[:80]} — ₹{c.get('price', 0):,.0f}"
        if c.get("rating"):
            line += f" | ★{c['rating']}"
        if c.get("review_count"):
            line += f" ({c['review_count']} reviews)"
        if c.get("source"):
            line += f" [{c['source']}]"
        comp_lines.append(line)

    competitors_text = "\n".join(comp_lines) if comp_lines else "  No competitor data scraped."

    desc_block = ""
    if product_description:
        desc_block = f"\nProduct Description:\n  {product_description[:500]}\n"

    insights_block = ""
    if rule_insights:
        insights_block = "\nRule-Based Insights (already computed):\n"
        for ins in rule_insights[:8]:
            insights_block += f"  • {ins}\n"

    prompt = f"""Analyse the competitive landscape for the following product and return a JSON object.

Product: {product_name}
Category: {category or 'General'}
My Price: ₹{my_price:,.2f}
{desc_block}
Market Summary:
  Average Price : ₹{market_summary.get('avg_market_price', 0):,.2f}
  Median Price  : ₹{market_summary.get('median_price', 0):,.2f}
  Min Price     : ₹{market_summary.get('min_price', 0):,.2f}
  Max Price     : ₹{market_summary.get('max_price', 0):,.2f}
  Price Spread  : ₹{market_summary.get('price_spread', 0):,.2f}
  Avg Rating    : {market_summary.get('avg_rating') or 'N/A'}
  Competitors   : {market_summary.get('competitor_count', 0)}

My Position:
  vs Market Avg : {position.get('price_vs_market_avg_percent', 0):+.1f}%
  vs Median     : {position.get('price_vs_median_percent', 0):+.1f}%
  Position      : {position.get('position', 'unknown')}
  Rank          : {position.get('rank_estimate', 'N/A')}

Competitors Found:
{competitors_text}
{insights_block}
Return ONLY this JSON (no extra text):
{{
  "executive_summary": "2-3 sentence overview of competitive position",
  "pricing_strategy": "specific pricing recommendation with reasoning",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "opportunities": ["opportunity 1", "opportunity 2"],
  "threats": ["threat 1", "threat 2"],
  "recommended_price": <float or null>,
  "action_items": ["action 1", "action 2", "action 3"],
  "market_analysis": "paragraph-length deep competitive analysis"
}}
"""
    return prompt


# ══════════════════════════════════════════════════════════════════
#  Normaliser – ensure all expected keys exist
# ══════════════════════════════════════════════════════════════════

def _normalise_analysis(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the parsed JSON has every required key with sane defaults."""
    return {
        "executive_summary": raw.get("executive_summary", ""),
        "pricing_strategy": raw.get("pricing_strategy", ""),
        "strengths": raw.get("strengths", []),
        "weaknesses": raw.get("weaknesses", []),
        "opportunities": raw.get("opportunities", []),
        "threats": raw.get("threats", []),
        "recommended_price": _try_float(raw.get("recommended_price")),
        "action_items": raw.get("action_items", []),
        "market_analysis": raw.get("market_analysis", ""),
    }


def _try_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
