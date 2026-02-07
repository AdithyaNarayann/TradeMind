"""
Competitive Intelligence - Rule-Based Insight Generator

Evaluates the seller's competitive position and generates actionable insights.

DESIGN DECISIONS:
- Pure rules, no ML, no external API calls
- Each rule is an independent evaluator function
- Insights have severity levels: info, warning, success, critical
- Insights have categories for frontend grouping
- All evaluators receive the same context dict and return 0+ insights
- Easy to add new rules: just add a function to EVALUATORS list
"""

import logging
from typing import List, Dict, Any, Callable

from .schemas import CompetitiveInsight, InsightSeverity

logger = logging.getLogger(__name__)

# Type alias for evaluator functions
Evaluator = Callable[[Dict[str, Any]], List[CompetitiveInsight]]


def generate_insights(
    my_price: float,
    market_summary: Dict[str, Any],
    position: Dict[str, Any]
) -> List[CompetitiveInsight]:
    """
    Run all insight evaluators and collect their outputs.
    
    Args:
        my_price: Seller's current price
        market_summary: Output from compute_market_summary()
        position: Output from compute_my_position()
        
    Returns:
        List of CompetitiveInsight objects, sorted by severity (critical first)
    """
    # Build context dict that all evaluators share
    context = {
        "my_price": my_price,
        "avg_market_price": market_summary.get("avg_market_price", 0),
        "min_price": market_summary.get("min_price", 0),
        "max_price": market_summary.get("max_price", 0),
        "median_price": market_summary.get("median_price", 0),
        "price_spread": market_summary.get("price_spread", 0),
        "avg_rating": market_summary.get("avg_rating"),
        "competitor_count": market_summary.get("competitor_count", 0),
        "price_vs_avg_pct": position.get("price_vs_market_avg_percent", 0),
        "position": position.get("position", "unknown"),
        "rank_estimate": position.get("rank_estimate", "N/A"),
        "percentile": position.get("percentile", 50),
    }
    
    insights = []
    for evaluator in _EVALUATORS:
        try:
            results = evaluator(context)
            insights.extend(results)
        except Exception as e:
            logger.error(f"Insight evaluator {evaluator.__name__} failed: {e}")
    
    # Sort: critical > warning > info > success
    severity_order = {
        InsightSeverity.CRITICAL: 0,
        InsightSeverity.WARNING: 1,
        InsightSeverity.INFO: 2,
        InsightSeverity.SUCCESS: 3,
    }
    insights.sort(key=lambda i: severity_order.get(i.severity, 99))
    
    return insights


# ============================================================
#  Individual Evaluators
#  Each returns a list of 0 or more CompetitiveInsight objects
# ============================================================

def _evaluate_pricing_position(ctx: Dict[str, Any]) -> List[CompetitiveInsight]:
    """Evaluate whether the price is competitive."""
    insights = []
    pct = ctx["price_vs_avg_pct"]
    position = ctx["position"]
    avg = ctx["avg_market_price"]
    my = ctx["my_price"]
    
    if avg <= 0:
        return insights
    
    if pct > 20:
        insights.append(CompetitiveInsight(
            message=f"Your price (₹{my:,.0f}) is {pct:.1f}% above the market average (₹{avg:,.0f}). "
                    f"Consider reducing to improve competitiveness unless you offer premium value.",
            severity=InsightSeverity.CRITICAL,
            category="pricing"
        ))
    elif pct > 10:
        insights.append(CompetitiveInsight(
            message=f"Your price is {pct:.1f}% above market average. "
                    f"This may reduce conversions for price-sensitive buyers.",
            severity=InsightSeverity.WARNING,
            category="pricing"
        ))
    elif pct < -15:
        insights.append(CompetitiveInsight(
            message=f"Your price is {abs(pct):.1f}% below market average. "
                    f"You may be leaving money on the table. Consider a moderate price increase.",
            severity=InsightSeverity.WARNING,
            category="pricing"
        ))
    elif pct < -5:
        insights.append(CompetitiveInsight(
            message=f"Your price is {abs(pct):.1f}% below market average — "
                    f"competitive positioning that should drive conversions.",
            severity=InsightSeverity.SUCCESS,
            category="pricing"
        ))
    else:
        insights.append(CompetitiveInsight(
            message=f"Your price is within 5% of the market average (₹{avg:,.0f}). "
                    f"Solid middle-ground positioning.",
            severity=InsightSeverity.INFO,
            category="pricing"
        ))
    
    return insights


def _evaluate_price_rank(ctx: Dict[str, Any]) -> List[CompetitiveInsight]:
    """Evaluate rank among competitors."""
    insights = []
    rank = ctx["rank_estimate"]
    total = ctx["competitor_count"]
    
    if total <= 0:
        return insights
    
    rank_label = ctx.get("rank_estimate", "N/A")
    
    if percentile >= 90:
        insights.append(CompetitiveInsight(
            message=f"You are among the most expensive options ({rank_label}). "
                    f"90%+ of competitors are priced lower.",
            severity=InsightSeverity.CRITICAL,
            category="rank"
        ))
    elif percentile <= 10:
        insights.append(CompetitiveInsight(
            message=f"You offer one of the lowest prices ({rank_label}). "
                    f"Strong price advantage — ensure margins are sustainable.",
            severity=InsightSeverity.SUCCESS,
            category="rank"
        ))
    
    return insights


def _evaluate_market_saturation(ctx: Dict[str, Any]) -> List[CompetitiveInsight]:
    """Evaluate how crowded the market is."""
    insights = []
    count = ctx["competitor_count"]
    spread = ctx["price_spread"]
    
    if count >= 15:
        insights.append(CompetitiveInsight(
            message=f"Highly competitive market with {count} competitors found. "
                    f"Differentiation through quality, branding, or bundling is essential.",
            severity=InsightSeverity.WARNING,
            category="market"
        ))
    elif count <= 3:
        insights.append(CompetitiveInsight(
            message=f"Low competition detected ({count} competitors). "
                    f"Opportunity to establish market presence or premium pricing.",
            severity=InsightSeverity.INFO,
            category="market"
        ))
    
    # Wide price spread indicates fragmented market
    avg_price = ctx.get("avg_market_price", 0)
    if spread > 0 and avg_price > 0:
        spread_pct = (spread / avg_price) * 100
        if spread_pct > 100:
            insights.append(CompetitiveInsight(
                message=f"Price spread is ₹{spread:,.0f} ({spread_pct:.0f}% of avg) — highly fragmented market. "
                        f"Multiple price tiers exist; target a specific segment.",
                severity=InsightSeverity.INFO,
                category="market"
            ))
    
    return insights


def _evaluate_price_proximity(ctx: Dict[str, Any]) -> List[CompetitiveInsight]:
    """
    Check if the seller's price is very close to the cheapest
    or most expensive competitor.
    """
    insights = []
    my = ctx["my_price"]
    min_p = ctx["min_price"]
    max_p = ctx["max_price"]
    
    if min_p <= 0 or max_p <= 0:
        return insights
    
    # Close to cheapest
    if min_p > 0:
        diff_from_min_pct = ((my - min_p) / min_p) * 100
        if 0 < diff_from_min_pct <= 5:
            insights.append(CompetitiveInsight(
                message=f"Your price is only {diff_from_min_pct:.1f}% above the cheapest option (₹{min_p:,.0f}). "
                        f"A small discount could make you the lowest-priced option.",
                severity=InsightSeverity.INFO,
                category="opportunity"
            ))
    
    # Close to most expensive
    if max_p > 0 and my > max_p * 0.95:
        insights.append(CompetitiveInsight(
            message=f"Your price is near the highest in the market (₹{max_p:,.0f}). "
                    f"Ensure your listing highlights premium value to justify the price.",
            severity=InsightSeverity.WARNING,
            category="opportunity"
        ))
    
    return insights


def _evaluate_median_strategy(ctx: Dict[str, Any]) -> List[CompetitiveInsight]:
    """Suggest strategies based on median price positioning."""
    insights = []
    my = ctx["my_price"]
    median_p = ctx["median_price"]
    
    if median_p <= 0:
        return insights
    
    diff_pct = ((my - median_p) / median_p) * 100
    
    if abs(diff_pct) <= 3:
        insights.append(CompetitiveInsight(
            message=f"Your price closely matches the market median (₹{median_p:,.0f}). "
                    f"Consider value-added bundling to differentiate without changing price.",
            severity=InsightSeverity.INFO,
            category="strategy"
        ))
    
    return insights


def _evaluate_no_data(ctx: Dict[str, Any]) -> List[CompetitiveInsight]:
    """Handle the case where no competitor data was found."""
    insights = []
    
    if ctx["competitor_count"] == 0:
        insights.append(CompetitiveInsight(
            message="No competitor data available. "
                    "This may indicate a niche product or scraping limitations. "
                    "Consider manual market research for better insights.",
            severity=InsightSeverity.WARNING,
            category="data_quality"
        ))
    
    return insights


# Registry of all evaluators (order matters for readability, not correctness)
_EVALUATORS: List[Evaluator] = [
    _evaluate_no_data,
    _evaluate_pricing_position,
    _evaluate_price_rank,
    _evaluate_market_saturation,
    _evaluate_price_proximity,
    _evaluate_median_strategy,
]
