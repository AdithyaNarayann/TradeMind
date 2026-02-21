"""
Insight Engine - Rule-Based Business Intelligence Generator

This module implements a rule-based insight system that:
- Evaluates business metrics against configurable thresholds
- Generates human-readable insights with severity levels
- Categories insights for easy filtering and display

All rules are pure functions with no side effects.
Easy to extend by adding new rule functions.
"""

from decimal import Decimal
from typing import List, Callable, Optional
from dataclasses import dataclass

from schemas.outputs import BusinessInsight, InsightSeverity
from schemas.inputs import ProductParameters, PerformanceSignals
from calculations.metrics import (
    RevenueMetrics,
    CostMetrics,
    ProfitMetrics,
    PerformanceRatios,
    UnitEconomics,
)


# =============================================================================
# THRESHOLD CONFIGURATION
# =============================================================================

@dataclass
class Thresholds:
    """
    Configurable thresholds for insight generation.
    
    These can be adjusted based on industry or seller preferences.
    Future: Load from config file or seller settings.
    """
    
    # Conversion thresholds
    conversion_excellent: Decimal = Decimal("25")
    conversion_good: Decimal = Decimal("15")
    conversion_warning: Decimal = Decimal("5")
    conversion_critical: Decimal = Decimal("2")
    
    # Return rate thresholds
    return_rate_good: Decimal = Decimal("3")
    return_rate_warning: Decimal = Decimal("8")
    return_rate_critical: Decimal = Decimal("15")
    
    # Profit margin thresholds
    margin_excellent: Decimal = Decimal("30")
    margin_good: Decimal = Decimal("15")
    margin_warning: Decimal = Decimal("5")
    
    # Sell-through thresholds
    sellthrough_excellent: Decimal = Decimal("80")
    sellthrough_good: Decimal = Decimal("50")
    sellthrough_warning: Decimal = Decimal("20")
    
    # ROI thresholds
    roi_excellent: Decimal = Decimal("300")
    roi_good: Decimal = Decimal("100")
    roi_warning: Decimal = Decimal("50")
    roi_critical: Decimal = Decimal("0")


# Default thresholds instance
DEFAULT_THRESHOLDS = Thresholds()


# =============================================================================
# INSIGHT RULE TYPE
# =============================================================================

@dataclass
class InsightRule:
    """
    Definition of an insight rule.
    
    Each rule is a function that takes metrics and returns an optional insight.
    """
    name: str
    category: str
    evaluate: Callable[..., Optional[BusinessInsight]]


# =============================================================================
# CONVERSION INSIGHTS
# =============================================================================

def _evaluate_conversion_rate(
    ratios: PerformanceRatios,
    performance: PerformanceSignals,
    thresholds: Thresholds
) -> Optional[BusinessInsight]:
    """Evaluate conversion rate and generate appropriate insight."""
    
    rate = ratios.conversion_rate
    
    # Skip if no chats
    if performance.chats == 0:
        return BusinessInsight(
            message="No customer inquiries recorded yet. Analytics will improve once conversations begin.",
            severity=InsightSeverity.INFO,
            category="conversion",
            metric_value=rate
        )
    
    if rate >= thresholds.conversion_excellent:
        return BusinessInsight(
            message=f"Excellent conversion rate of {rate}%! Your customer engagement is outstanding.",
            severity=InsightSeverity.SUCCESS,
            category="conversion",
            metric_value=rate,
            threshold=thresholds.conversion_excellent
        )
    
    if rate >= thresholds.conversion_good:
        return BusinessInsight(
            message=f"Strong conversion rate of {rate}%. Keep up the good work!",
            severity=InsightSeverity.SUCCESS,
            category="conversion",
            metric_value=rate,
            threshold=thresholds.conversion_good
        )
    
    if rate >= thresholds.conversion_warning:
        return BusinessInsight(
            message=f"Conversion rate is {rate}%. Consider improving product descriptions or response time.",
            severity=InsightSeverity.INFO,
            category="conversion",
            metric_value=rate,
            threshold=thresholds.conversion_warning
        )
    
    if rate >= thresholds.conversion_critical:
        return BusinessInsight(
            message=f"Low conversion rate of {rate}%. Many inquiries aren't converting to sales. Review pricing, product info, or negotiation tactics.",
            severity=InsightSeverity.WARNING,
            category="conversion",
            metric_value=rate,
            threshold=thresholds.conversion_critical
        )
    
    return BusinessInsight(
        message=f"Critical: Conversion rate is only {rate}%. Urgent review needed - most customers are leaving without purchasing.",
        severity=InsightSeverity.CRITICAL,
        category="conversion",
        metric_value=rate,
        threshold=thresholds.conversion_critical
    )


# =============================================================================
# PROFIT INSIGHTS
# =============================================================================

def _evaluate_profit_status(
    profit: ProfitMetrics,
    costs: CostMetrics,
    thresholds: Thresholds
) -> Optional[BusinessInsight]:
    """Evaluate profit/loss status."""
    
    if profit.profit_status == "LOSS":
        return BusinessInsight(
            message=f"⚠️ You are selling at a LOSS of ₹{abs(profit.profit_or_loss):.2f}. Total costs exceed revenue.",
            severity=InsightSeverity.CRITICAL,
            category="profit",
            metric_value=profit.profit_or_loss
        )
    
    if profit.profit_status == "BREAK_EVEN":
        return BusinessInsight(
            message="You are at break-even. Revenue equals costs with no profit.",
            severity=InsightSeverity.WARNING,
            category="profit",
            metric_value=profit.profit_or_loss
        )
    
    # It's a profit - evaluate margin
    margin = profit.profit_margin_percent
    
    if margin >= thresholds.margin_excellent:
        return BusinessInsight(
            message=f"Excellent profit margin of {margin}%! Your pricing strategy is working well.",
            severity=InsightSeverity.SUCCESS,
            category="profit",
            metric_value=margin,
            threshold=thresholds.margin_excellent
        )
    
    if margin >= thresholds.margin_good:
        return BusinessInsight(
            message=f"Healthy profit margin of {margin}%. Good balance of volume and profit.",
            severity=InsightSeverity.SUCCESS,
            category="profit",
            metric_value=margin,
            threshold=thresholds.margin_good
        )
    
    if margin >= thresholds.margin_warning:
        return BusinessInsight(
            message=f"Profit margin is {margin}%. Consider if higher margins are achievable.",
            severity=InsightSeverity.INFO,
            category="profit",
            metric_value=margin,
            threshold=thresholds.margin_warning
        )
    
    return BusinessInsight(
        message=f"Thin profit margin of only {margin}%. Small cost increases could push you into loss.",
        severity=InsightSeverity.WARNING,
        category="profit",
        metric_value=margin,
        threshold=thresholds.margin_warning
    )


# =============================================================================
# RETURN INSIGHTS
# =============================================================================

def _evaluate_return_rate(
    ratios: PerformanceRatios,
    revenue: RevenueMetrics,
    thresholds: Thresholds
) -> Optional[BusinessInsight]:
    """Evaluate return rate."""
    
    rate = ratios.return_rate
    
    # Skip if no sales
    if revenue.units_sold == 0:
        return None
    
    if rate == 0:
        return BusinessInsight(
            message="Zero returns - excellent product satisfaction!",
            severity=InsightSeverity.SUCCESS,
            category="returns",
            metric_value=rate
        )
    
    if rate <= thresholds.return_rate_good:
        return BusinessInsight(
            message=f"Low return rate of {rate}%. Customer satisfaction is good.",
            severity=InsightSeverity.SUCCESS,
            category="returns",
            metric_value=rate,
            threshold=thresholds.return_rate_good
        )
    
    if rate <= thresholds.return_rate_warning:
        return BusinessInsight(
            message=f"Return rate is {rate}%. Monitor for patterns in return reasons.",
            severity=InsightSeverity.INFO,
            category="returns",
            metric_value=rate,
            threshold=thresholds.return_rate_warning
        )
    
    if rate <= thresholds.return_rate_critical:
        return BusinessInsight(
            message=f"High return rate of {rate}%. Investigate product quality or listing accuracy.",
            severity=InsightSeverity.WARNING,
            category="returns",
            metric_value=rate,
            threshold=thresholds.return_rate_critical
        )
    
    return BusinessInsight(
        message=f"Critical: Return rate is {rate}%! This severely impacts profitability. Urgent quality review needed.",
        severity=InsightSeverity.CRITICAL,
        category="returns",
        metric_value=rate,
        threshold=thresholds.return_rate_critical
    )


# =============================================================================
# INVENTORY INSIGHTS
# =============================================================================

def _evaluate_inventory(
    ratios: PerformanceRatios,
    product: ProductParameters,
    remaining_stock: int,
    thresholds: Thresholds
) -> Optional[BusinessInsight]:
    """Evaluate inventory sell-through."""
    
    rate = ratios.sell_through_rate
    
    if product.initial_stock == 0:
        return BusinessInsight(
            message="No initial stock defined.",
            severity=InsightSeverity.INFO,
            category="inventory",
            metric_value=rate
        )
    
    if rate >= thresholds.sellthrough_excellent:
        if remaining_stock <= 0:
            return BusinessInsight(
                message="Stock is depleted! Consider restocking to meet demand.",
                severity=InsightSeverity.WARNING,
                category="inventory",
                metric_value=rate
            )
        return BusinessInsight(
            message=f"Fast-moving inventory with {rate}% sell-through! Only {remaining_stock} units remaining.",
            severity=InsightSeverity.SUCCESS,
            category="inventory",
            metric_value=rate,
            threshold=thresholds.sellthrough_excellent
        )
    
    if rate >= thresholds.sellthrough_good:
        return BusinessInsight(
            message=f"Good sell-through rate of {rate}%. {remaining_stock} units still available.",
            severity=InsightSeverity.SUCCESS,
            category="inventory",
            metric_value=rate,
            threshold=thresholds.sellthrough_good
        )
    
    if rate >= thresholds.sellthrough_warning:
        return BusinessInsight(
            message=f"Sell-through is {rate}%. {remaining_stock} units may need promotional push.",
            severity=InsightSeverity.INFO,
            category="inventory",
            metric_value=rate,
            threshold=thresholds.sellthrough_warning
        )
    
    return BusinessInsight(
        message=f"Slow inventory movement at {rate}% sell-through. Consider pricing adjustments or promotions.",
        severity=InsightSeverity.WARNING,
        category="inventory",
        metric_value=rate,
        threshold=thresholds.sellthrough_warning
    )


# =============================================================================
# MARKETING/ROI INSIGHTS
# =============================================================================

def _evaluate_marketing_roi(
    ratios: PerformanceRatios,
    costs: CostMetrics,
    thresholds: Thresholds
) -> Optional[BusinessInsight]:
    """Evaluate marketing ROI if applicable."""
    
    # Skip if no marketing spend
    if costs.marketing_cost == 0:
        return None
    
    roi = ratios.roi
    if roi is None:
        return None
    
    if roi >= thresholds.roi_excellent:
        return BusinessInsight(
            message=f"Outstanding marketing ROI of {roi}%! Your advertising is highly effective.",
            severity=InsightSeverity.SUCCESS,
            category="marketing",
            metric_value=roi,
            threshold=thresholds.roi_excellent
        )
    
    if roi >= thresholds.roi_good:
        return BusinessInsight(
            message=f"Good marketing ROI of {roi}%. Ad spend is paying off.",
            severity=InsightSeverity.SUCCESS,
            category="marketing",
            metric_value=roi,
            threshold=thresholds.roi_good
        )
    
    if roi >= thresholds.roi_warning:
        return BusinessInsight(
            message=f"Marketing ROI is {roi}%. Consider optimizing ad targeting.",
            severity=InsightSeverity.INFO,
            category="marketing",
            metric_value=roi,
            threshold=thresholds.roi_warning
        )
    
    if roi >= thresholds.roi_critical:
        return BusinessInsight(
            message=f"Low marketing ROI of {roi}%. Ad spend may need reevaluation.",
            severity=InsightSeverity.WARNING,
            category="marketing",
            metric_value=roi,
            threshold=thresholds.roi_critical
        )
    
    return BusinessInsight(
        message=f"Negative marketing ROI ({roi}%). Marketing spend exceeds returns - pause or restructure campaigns.",
        severity=InsightSeverity.CRITICAL,
        category="marketing",
        metric_value=roi,
        threshold=thresholds.roi_critical
    )


# =============================================================================
# UNIT ECONOMICS INSIGHTS
# =============================================================================

def _evaluate_unit_economics(
    unit_econ: UnitEconomics,
    product: ProductParameters
) -> Optional[BusinessInsight]:
    """Evaluate per-unit economics."""
    
    if unit_econ.profit_per_unit < 0:
        return BusinessInsight(
            message=f"Losing ₹{abs(unit_econ.profit_per_unit):.2f} per unit sold. Price increase or cost reduction needed.",
            severity=InsightSeverity.CRITICAL,
            category="unit_economics",
            metric_value=unit_econ.profit_per_unit
        )
    
    # Check if effective price is significantly lower
    price_drop_pct = ((product.selling_price - unit_econ.effective_selling_price) / product.selling_price) * 100
    
    if price_drop_pct >= 15:
        return BusinessInsight(
            message=f"Platform fees reduce your effective price by {price_drop_pct:.1f}% (₹{product.selling_price} → ₹{unit_econ.effective_selling_price}).",
            severity=InsightSeverity.INFO,
            category="unit_economics",
            metric_value=price_drop_pct
        )
    
    return None


# =============================================================================
# MAIN INSIGHT GENERATOR
# =============================================================================

def generate_insights(
    product: ProductParameters,
    performance: PerformanceSignals,
    revenue: RevenueMetrics,
    costs: CostMetrics,
    profit: ProfitMetrics,
    ratios: PerformanceRatios,
    unit_econ: UnitEconomics,
    remaining_stock: int,
    thresholds: Optional[Thresholds] = None
) -> List[BusinessInsight]:
    """
    Generate all business insights based on calculated metrics.
    
    This is the main entry point for the insights module.
    It evaluates all rules and returns applicable insights.
    
    Args:
        product: Product parameters
        performance: Performance signals
        revenue: Revenue metrics
        costs: Cost metrics
        profit: Profit metrics
        ratios: Performance ratios
        unit_econ: Unit economics
        remaining_stock: Current inventory level
        thresholds: Optional custom thresholds (uses defaults if None)
        
    Returns:
        List of BusinessInsight objects, sorted by severity
    """
    thresholds = thresholds or DEFAULT_THRESHOLDS
    insights: List[BusinessInsight] = []
    
    # Evaluate all insight rules
    evaluators = [
        lambda: _evaluate_profit_status(profit, costs, thresholds),
        lambda: _evaluate_conversion_rate(ratios, performance, thresholds),
        lambda: _evaluate_return_rate(ratios, revenue, thresholds),
        lambda: _evaluate_inventory(ratios, product, remaining_stock, thresholds),
        lambda: _evaluate_marketing_roi(ratios, costs, thresholds),
        lambda: _evaluate_unit_economics(unit_econ, product),
    ]
    
    for evaluator in evaluators:
        insight = evaluator()
        if insight is not None:
            insights.append(insight)
    
    # Sort by severity (critical first)
    severity_order = {
        InsightSeverity.CRITICAL: 0,
        InsightSeverity.WARNING: 1,
        InsightSeverity.INFO: 2,
        InsightSeverity.SUCCESS: 3,
    }
    
    insights.sort(key=lambda x: severity_order.get(x.severity, 99))
    
    return insights
