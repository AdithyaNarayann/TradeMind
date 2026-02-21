"""
Analytics Service - Business Logic Orchestration

This service layer orchestrates:
1. Input validation (via Pydantic)
2. Metric calculations
3. Chart data generation
4. Insight generation
5. Response assembly

Designed to be easily injectable for testing.
"""

from schemas.inputs import AnalyticsRequest, ProductParameters, PerformanceSignals
from schemas.outputs import (
    AnalyticsResponse,
    SummaryMetrics,
    AnalyticsMeta,
    ProfitStatus,
)
from calculations import calculate_all_metrics, build_all_charts
from insights import generate_insights


class AnalyticsService:
    """
    Stateless analytics service.
    
    All methods are pure - same inputs always produce same outputs.
    No database, no side effects, no global state.
    
    This design allows:
    - Easy unit testing
    - Horizontal scaling
    - Future database integration without logic changes
    """
    
    def calculate(self, request: AnalyticsRequest) -> AnalyticsResponse:
        """
        Execute the full analytics pipeline.
        
        Steps:
        1. Extract input data
        2. Calculate all metrics
        3. Build chart data
        4. Generate insights
        5. Assemble response
        
        Args:
            request: Validated analytics request
            
        Returns:
            Complete AnalyticsResponse with all data
        """
        product = request.product
        performance = request.performance
        
        # Step 1: Calculate all metrics
        revenue, costs, profit, ratios, unit_econ, remaining_stock = calculate_all_metrics(
            product=product,
            performance=performance
        )
        
        # Step 2: Build chart data
        charts = build_all_charts(
            product=product,
            performance=performance,
            revenue=revenue,
            costs=costs,
            profit=profit
        )
        
        # Step 3: Generate insights
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
        
        # Step 4: Assemble summary metrics
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
        
        # Step 5: Build metadata
        meta = self._build_meta(product, performance, profit, costs)
        
        # Step 6: Assemble final response
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
        """Build response metadata."""
        
        warnings = []
        
        # Check for data quality issues
        if performance.chats == 0 and performance.orders > 0:
            warnings.append("Orders exist but no chats recorded")
        
        if performance.units_sold == 0:
            warnings.append("No sales data - metrics are projections")
        
        has_sufficient_data = (
            performance.orders > 0 or 
            performance.units_sold > 0
        )
        
        return AnalyticsMeta(
            is_profitable=profit.profit_status == "PROFIT",
            is_break_even=profit.profit_status == "BREAK_EVEN",
            has_marketing_data=costs.marketing_cost > 0,
            has_sufficient_data=has_sufficient_data,
            simulation_ready=True,
            warnings=warnings
        )


# Singleton instance for route handlers
analytics_service = AnalyticsService()
