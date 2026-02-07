"""
Competitive Intelligence Module

An OPTIONAL, additive feature that provides market intelligence
by scraping publicly accessible product listings and computing
competitive positioning insights.

This module is designed as an isolated plugin:
- If it fails, the rest of the analytics engine is unaffected
- No shared mutable state with other modules
- All functions are pure where possible
- Graceful fallback when scraping fails

Architecture:
    Request → Scraper → Normalizer → Comparison → Insights → LLM Analysis → Response
"""

from .routes import router as competitive_router
from .llm_analyzer import generate_llm_analysis

__all__ = [
    "competitive_router",
    "generate_llm_analysis",
]
