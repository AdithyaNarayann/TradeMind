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
    Request → Scraper → Normalizer → Comparison → Insights → Response
"""

from .routes import router as competitive_router

__all__ = [
    "competitive_router",
]
