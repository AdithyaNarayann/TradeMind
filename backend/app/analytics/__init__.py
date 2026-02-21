"""
Business Analytics Module

Stateless analytics engine for seller dashboards.
Integrates with the main negotiation API.
"""

from .schemas import (
    ProductParameters,
    PerformanceSignals,
    AnalyticsRequest,
    SummaryMetrics,
    ChartsData,
    BusinessInsight,
    AnalyticsMeta,
    AnalyticsResponse,
)

from .service import AnalyticsService, analytics_service
from .routes import router as analytics_router

__all__ = [
    # Schemas
    "ProductParameters",
    "PerformanceSignals", 
    "AnalyticsRequest",
    "SummaryMetrics",
    "ChartsData",
    "BusinessInsight",
    "AnalyticsMeta",
    "AnalyticsResponse",
    # Service
    "AnalyticsService",
    "analytics_service",
    # Router
    "analytics_router",
]
