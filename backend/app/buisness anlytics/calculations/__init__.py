"""
Calculations Module - Pure Functions for Business Metrics

All calculation functions are stateless and deterministic.
No database access, no side effects, no global state.
"""

from .metrics import (
    calculate_revenue,
    calculate_costs,
    calculate_profit_metrics,
    calculate_performance_ratios,
    calculate_unit_economics,
    calculate_all_metrics,
)

from .charts import (
    build_revenue_chart,
    build_funnel_chart,
    build_inventory_chart,
    build_cost_breakdown_chart,
    build_all_charts,
)

__all__ = [
    # Metric calculations
    "calculate_revenue",
    "calculate_costs",
    "calculate_profit_metrics",
    "calculate_performance_ratios",
    "calculate_unit_economics",
    "calculate_all_metrics",
    # Chart builders
    "build_revenue_chart",
    "build_funnel_chart",
    "build_inventory_chart",
    "build_cost_breakdown_chart",
    "build_all_charts",
]
