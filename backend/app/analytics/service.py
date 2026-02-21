"""
Analytics Service - Business Logic Orchestration

Stateless service that orchestrates the analytics pipeline.
"""

from .schemas import (
    AnalyticsRequest,
    AnalyticsResponse,
    SummaryMetrics,
    AnalyticsMeta,
    ProfitStatus,
    ProductParameters,
    PerformanceSignals,
)
from .calculations import calculate_all_metrics, build_all_charts
from .insights import generate_insights


class AnalyticsService:
    """
    Stateless analytics service.
    
    All methods are pure - same inputs always produce same outputs.
    """
    
    def calculate(self, request: AnalyticsRequest) -> AnalyticsResponse:
        """Execute the full analytics pipeline."""
        product = request.product
        performance = request.performance
        
        # Calculate all metrics
        revenue, costs, profit, ratios, unit_econ, remaining_stock = calculate_all_metrics(
            product=product,
            performance=performance
        )
        
        # Build chart data
        charts = build_all_charts(
            product=product,
            performance=performance,
            revenue=revenue,
            costs=costs,
            profit=profit
        )
        
        # Generate insights
        insights = generate_insights(
            product=product,
            performance=performance,
            revenue=revenue,
            costs=costs,
            profit=profit,
            ratios=ratios,
            unit_econ=unit_econ,
            remaining_stock=remaining_stock
        )
        
        # Assemble summary metrics
        summary = SummaryMetrics(
            gross_revenue=revenue.gross_revenue,
            net_revenue=revenue.net_revenue,
            product_cost=costs.product_cost,
            platform_fee=costs.platform_fee,
            shipping_total=costs.shipping_total,
            marketing_cost=costs.marketing_cost,
            total_cost=costs.total_cost,
            profit_or_loss=profit.profit_or_loss,
            profit_status=ProfitStatus(profit.profit_status),
            profit_margin_percent=profit.profit_margin_percent,
            conversion_rate=ratios.conversion_rate,
            sell_through_rate=ratios.sell_through_rate,
            return_rate=ratios.return_rate,
            roi=ratios.roi,
            profit_per_unit=unit_econ.profit_per_unit,
            effective_selling_price=unit_econ.effective_selling_price,
            remaining_stock=remaining_stock,
            net_units_sold=revenue.net_units_sold
        )
        
        # Build metadata
        meta = self._build_meta(product, performance, profit, costs)
        
        return AnalyticsResponse(
            summary_metrics=summary,
            charts=charts,
            insights=insights,
            meta=meta
        )
    
    def _build_meta(
        self,
        product: ProductParameters,
        performance: PerformanceSignals,
        profit,
        costs
    ) -> AnalyticsMeta:
        warnings = []
        
        if performance.chats == 0 and performance.orders > 0:
            warnings.append("Orders exist but no chats recorded")
        
        if performance.units_sold == 0:
            warnings.append("No sales data - metrics are projections")
        
        has_sufficient_data = performance.orders > 0 or performance.units_sold > 0
        
        return AnalyticsMeta(
            is_profitable=profit.profit_status == "PROFIT",
            is_break_even=profit.profit_status == "BREAK_EVEN",
            has_marketing_data=costs.marketing_cost > 0,
            has_sufficient_data=has_sufficient_data,
            simulation_ready=True,
            warnings=warnings
        )


# Singleton instance
analytics_service = AnalyticsService()
