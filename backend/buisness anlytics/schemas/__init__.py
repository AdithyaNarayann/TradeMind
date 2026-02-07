"""
Schemas Module - Pydantic Models for Analytics Engine

All input validation and output structures are defined here.
Strict typing ensures data integrity across the analytics pipeline.
"""

from .inputs import (
    ProductParameters,
    PerformanceSignals,
    AnalyticsRequest,
)

from .outputs import (
    SummaryMetrics,
    BarChartData,
    FunnelChartData,
    InventoryChartData,
    ChartsData,
    AnalyticsMeta,
    AnalyticsResponse,
)

__all__ = [
    # Inputs
    "ProductParameters",
    "PerformanceSignals",
    "AnalyticsRequest",
    # Outputs
    "SummaryMetrics",
    "BarChartData",
    "FunnelChartData",
    "InventoryChartData",
    "ChartsData",
    "AnalyticsMeta",
    "AnalyticsResponse",
]
