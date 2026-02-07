"""
Analytics Insights Engine - Rule-Based Business Intelligence

Generates human-readable insights based on calculated metrics.
"""

from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass

from .schemas import (
    BusinessInsight,
    InsightSeverity,
    ProductParameters,
    PerformanceSignals,
)
from .calculations import (
    RevenueMetrics,
    CostMetrics,
    ProfitMetrics,
    PerformanceRatios,
    UnitEconomics,
)


@dataclass
class Thresholds:
    """Configurable thresholds for insight generation."""
    conversion_excellent: Decimal = Decimal("25")
    conversion_good: Decimal = Decimal("15")
    conversion_warning: Decimal = Decimal("5")
    conversion_critical: Decimal = Decimal("2")
    
    return_rate_good: Decimal = Decimal("3")
    return_rate_warning: Decimal = Decimal("8")
    return_rate_critical: Decimal = Decimal("15")
    
    margin_excellent: Decimal = Decimal("30")
    margin_good: Decimal = Decimal("15")
    margin_warning: Decimal = Decimal("5")
    
    sellthrough_excellent: Decimal = Decimal("80")
    sellthrough_good: Decimal = Decimal("50")
    sellthrough_warning: Decimal = Decimal("20")
    
    roi_excellent: Decimal = Decimal("300")
    roi_good: Decimal = Decimal("100")
    roi_warning: Decimal = Decimal("50")
    roi_critical: Decimal = Decimal("0")


DEFAULT_THRESHOLDS = Thresholds()


def _evaluate_conversion_rate(
    ratios: PerformanceRatios,
    performance: PerformanceSignals,
    thresholds: Thresholds
) -> Optional[BusinessInsight]:
    rate = ratios.conversion_rate
    
    if performance.chats == 0:
        return BusinessInsight(
            message="No customer inquiries recorded yet.",
            severity=InsightSeverity.INFO,
            category="conversion",
            metric_value=rate
        )
    
    if rate >= thresholds.conversion_excellent:
        return BusinessInsight(
            message=f"Excellent conversion rate of {rate}%!",
            severity=InsightSeverity.SUCCESS,
            category="conversion",
            metric_value=rate,
            threshold=thresholds.conversion_excellent
        )
    
    if rate >= thresholds.conversion_good:
        return BusinessInsight(
            message=f"Strong conversion rate of {rate}%.",
            severity=InsightSeverity.SUCCESS,
            category="conversion",
            metric_value=rate,
            threshold=thresholds.conversion_good
        )
    
    if rate >= thresholds.conversion_warning:
        return BusinessInsight(
            message=f"Conversion rate is {rate}%. Consider improving product descriptions.",
            severity=InsightSeverity.INFO,
            category="conversion",
            metric_value=rate,
            threshold=thresholds.conversion_warning
        )
    
    if rate >= thresholds.conversion_critical:
        return BusinessInsight(
            message=f"Low conversion rate of {rate}%. Review pricing or negotiation tactics.",
            severity=InsightSeverity.WARNING,
            category="conversion",
            metric_value=rate,
            threshold=thresholds.conversion_critical
        )
    
    return BusinessInsight(
        message=f"Critical: Conversion rate is only {rate}%. Urgent review needed.",
        severity=InsightSeverity.CRITICAL,
        category="conversion",
        metric_value=rate,
        threshold=thresholds.conversion_critical
    )


def _evaluate_profit_status(
    profit: ProfitMetrics,
    costs: CostMetrics,
    thresholds: Thresholds
) -> Optional[BusinessInsight]:
    if profit.profit_status == "LOSS":
        return BusinessInsight(
            message=f"You are selling at a LOSS of ₹{abs(profit.profit_or_loss):.2f}.",
            severity=InsightSeverity.CRITICAL,
            category="profit",
            metric_value=profit.profit_or_loss
        )
    
    if profit.profit_status == "BREAK_EVEN":
        return BusinessInsight(
            message="You are at break-even. Revenue equals costs.",
            severity=InsightSeverity.WARNING,
            category="profit",
            metric_value=profit.profit_or_loss
        )
    
    margin = profit.profit_margin_percent
    
    if margin >= thresholds.margin_excellent:
        return BusinessInsight(
            message=f"Excellent profit margin of {margin}%!",
            severity=InsightSeverity.SUCCESS,
            category="profit",
            metric_value=margin,
            threshold=thresholds.margin_excellent
        )
    
    if margin >= thresholds.margin_good:
        return BusinessInsight(
            message=f"Healthy profit margin of {margin}%.",
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
        message=f"Thin profit margin of only {margin}%.",
        severity=InsightSeverity.WARNING,
        category="profit",
        metric_value=margin,
        threshold=thresholds.margin_warning
    )


def _evaluate_return_rate(
    ratios: PerformanceRatios,
    revenue: RevenueMetrics,
    thresholds: Thresholds
) -> Optional[BusinessInsight]:
    rate = ratios.return_rate
    
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
            message=f"Low return rate of {rate}%.",
            severity=InsightSeverity.SUCCESS,
            category="returns",
            metric_value=rate,
            threshold=thresholds.return_rate_good
        )
    
    if rate <= thresholds.return_rate_warning:
        return BusinessInsight(
            message=f"Return rate is {rate}%. Monitor for patterns.",
            severity=InsightSeverity.INFO,
            category="returns",
            metric_value=rate,
            threshold=thresholds.return_rate_warning
        )
    
    if rate <= thresholds.return_rate_critical:
        return BusinessInsight(
            message=f"High return rate of {rate}%. Investigate product quality.",
            severity=InsightSeverity.WARNING,
            category="returns",
            metric_value=rate,
            threshold=thresholds.return_rate_critical
        )
    
    return BusinessInsight(
        message=f"Critical: Return rate is {rate}%! Urgent quality review needed.",
        severity=InsightSeverity.CRITICAL,
        category="returns",
        metric_value=rate,
        threshold=thresholds.return_rate_critical
    )


def _evaluate_inventory(
    ratios: PerformanceRatios,
    product: ProductParameters,
    remaining_stock: int,
    thresholds: Thresholds
) -> Optional[BusinessInsight]:
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
                message="Stock is depleted! Consider restocking.",
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
            message=f"Good sell-through rate of {rate}%. {remaining_stock} units available.",
            severity=InsightSeverity.SUCCESS,
            category="inventory",
            metric_value=rate,
            threshold=thresholds.sellthrough_good
        )
    
    if rate >= thresholds.sellthrough_warning:
        return BusinessInsight(
            message=f"Sell-through is {rate}%. {remaining_stock} units may need promotion.",
            severity=InsightSeverity.INFO,
            category="inventory",
            metric_value=rate,
            threshold=thresholds.sellthrough_warning
        )
    
    return BusinessInsight(
        message=f"Slow inventory movement at {rate}% sell-through.",
        severity=InsightSeverity.WARNING,
        category="inventory",
        metric_value=rate,
        threshold=thresholds.sellthrough_warning
    )


def _evaluate_marketing_roi(
    ratios: PerformanceRatios,
    costs: CostMetrics,
    thresholds: Thresholds
) -> Optional[BusinessInsight]:
    if costs.marketing_cost == 0:
        return None
    
    roi = ratios.roi
    if roi is None:
        return None
    
    if roi >= thresholds.roi_excellent:
        return BusinessInsight(
            message=f"Outstanding marketing ROI of {roi}%!",
            severity=InsightSeverity.SUCCESS,
            category="marketing",
            metric_value=roi,
            threshold=thresholds.roi_excellent
        )
    
    if roi >= thresholds.roi_good:
        return BusinessInsight(
            message=f"Good marketing ROI of {roi}%.",
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
            message=f"Low marketing ROI of {roi}%.",
            severity=InsightSeverity.WARNING,
            category="marketing",
            metric_value=roi,
            threshold=thresholds.roi_critical
        )
    
    return BusinessInsight(
        message=f"Negative marketing ROI ({roi}%). Consider pausing campaigns.",
        severity=InsightSeverity.CRITICAL,
        category="marketing",
        metric_value=roi,
        threshold=thresholds.roi_critical
    )


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
    """Generate all business insights based on calculated metrics."""
    thresholds = thresholds or DEFAULT_THRESHOLDS
    insights: List[BusinessInsight] = []
    
    evaluators = [
        lambda: _evaluate_profit_status(profit, costs, thresholds),
        lambda: _evaluate_conversion_rate(ratios, performance, thresholds),
        lambda: _evaluate_return_rate(ratios, revenue, thresholds),
        lambda: _evaluate_inventory(ratios, product, remaining_stock, thresholds),
        lambda: _evaluate_marketing_roi(ratios, costs, thresholds),
    ]
    
    for evaluator in evaluators:
        insight = evaluator()
        if insight is not None:
            insights.append(insight)
    
    severity_order = {
        InsightSeverity.CRITICAL: 0,
        InsightSeverity.WARNING: 1,
        InsightSeverity.INFO: 2,
        InsightSeverity.SUCCESS: 3,
    }
    
    insights.sort(key=lambda x: severity_order.get(x.severity, 99))
    
    return insights
