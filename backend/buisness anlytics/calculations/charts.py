"""
Chart Data Builders - Transform Metrics into Chart-Ready Structures

These functions transform calculated metrics into formats
that can be directly consumed by frontend chart libraries.

All functions are pure and stateless.
"""

from decimal import Decimal
from typing import List

from schemas.outputs import (
    BarChartData,
    FunnelChartData,
    FunnelStage,
    InventoryChartData,
    ChartDataPoint,
    ChartsData,
)
from schemas.inputs import ProductParameters, PerformanceSignals
from .metrics import (
    RevenueMetrics,
    CostMetrics,
    ProfitMetrics,
    round_currency,
    safe_percentage,
)


# =============================================================================
# COLOR PALETTE
# =============================================================================

COLORS = {
    "revenue": "#22c55e",      # Green
    "cost": "#ef4444",         # Red
    "profit": "#3b82f6",       # Blue
    "loss": "#f97316",         # Orange
    "neutral": "#6b7280",      # Gray
    "product_cost": "#8b5cf6", # Purple
    "platform_fee": "#ec4899", # Pink
    "shipping": "#f59e0b",     # Amber
    "marketing": "#06b6d4",    # Cyan
    "sold": "#22c55e",         # Green
    "remaining": "#3b82f6",    # Blue
    "returned": "#ef4444",     # Red
    "chats": "#6366f1",        # Indigo
    "orders": "#8b5cf6",       # Purple
    "units": "#22c55e",        # Green
}


# =============================================================================
# CHART BUILDERS
# =============================================================================

def build_revenue_chart(
    revenue: RevenueMetrics,
    costs: CostMetrics,
    profit: ProfitMetrics
) -> BarChartData:
    """
    Build bar chart data for revenue vs cost vs profit visualization.
    
    Format compatible with Chart.js, Recharts, ECharts, etc.
    
    Args:
        revenue: Revenue metrics
        costs: Cost metrics
        profit: Profit metrics
        
    Returns:
        BarChartData ready for frontend rendering
    """
    profit_color = COLORS["profit"] if profit.profit_or_loss >= 0 else COLORS["loss"]
    
    return BarChartData(
        title="Revenue vs Cost vs Profit",
        labels=["Revenue", "Total Cost", "Profit/Loss"],
        datasets=[
            {
                "label": "Amount",
                "data": [
                    float(revenue.net_revenue),
                    float(costs.total_cost),
                    float(profit.profit_or_loss)
                ],
                "backgroundColor": [
                    COLORS["revenue"],
                    COLORS["cost"],
                    profit_color
                ],
                "borderColor": [
                    COLORS["revenue"],
                    COLORS["cost"],
                    profit_color
                ],
                "borderWidth": 1
            }
        ]
    )


def build_funnel_chart(
    performance: PerformanceSignals,
    revenue: RevenueMetrics
) -> FunnelChartData:
    """
    Build funnel chart data for sales conversion visualization.
    
    Shows: Chats → Orders → Units Sold → Net Sales
    
    Each stage shows the percentage relative to the previous stage.
    
    Args:
        performance: Performance signals
        revenue: Revenue metrics
        
    Returns:
        FunnelChartData with stages and percentages
    """
    chats = performance.chats
    orders = performance.orders
    units_sold = revenue.units_sold
    net_units = revenue.net_units_sold
    
    stages = []
    
    # Stage 1: Chats (always 100%)
    stages.append(FunnelStage(
        stage="Inquiries",
        value=chats,
        percentage=Decimal("100.00"),
        color=COLORS["chats"]
    ))
    
    # Stage 2: Orders (% of chats)
    orders_pct = safe_percentage(Decimal(orders), Decimal(chats)) if chats > 0 else Decimal("0")
    stages.append(FunnelStage(
        stage="Orders",
        value=orders,
        percentage=orders_pct,
        color=COLORS["orders"]
    ))
    
    # Stage 3: Units Sold (% of orders - can be >100% if bulk orders)
    units_pct = safe_percentage(Decimal(units_sold), Decimal(orders)) if orders > 0 else Decimal("0")
    stages.append(FunnelStage(
        stage="Units Sold",
        value=units_sold,
        percentage=units_pct,
        color=COLORS["units"]
    ))
    
    # Stage 4: Net Sales after returns (% of units sold)
    net_pct = safe_percentage(Decimal(net_units), Decimal(units_sold)) if units_sold > 0 else Decimal("0")
    stages.append(FunnelStage(
        stage="Net Sales",
        value=net_units,
        percentage=net_pct,
        color=COLORS["sold"]
    ))
    
    return FunnelChartData(
        title="Sales Funnel",
        stages=stages
    )


def build_inventory_chart(
    product: ProductParameters,
    revenue: RevenueMetrics
) -> InventoryChartData:
    """
    Build inventory status chart data for pie/donut visualization.
    
    Shows: Sold vs Remaining vs Returned
    
    Args:
        product: Product parameters (for initial stock)
        revenue: Revenue metrics (for sales figures)
        
    Returns:
        InventoryChartData with segments
    """
    initial_stock = product.initial_stock
    net_sold = revenue.net_units_sold
    returns = revenue.returns
    remaining = initial_stock - net_sold
    
    segments = [
        ChartDataPoint(
            label="Sold",
            value=Decimal(net_sold),
            color=COLORS["sold"]
        ),
        ChartDataPoint(
            label="Remaining",
            value=Decimal(remaining),
            color=COLORS["remaining"]
        ),
    ]
    
    # Only show returns segment if there are returns
    if returns > 0:
        segments.append(ChartDataPoint(
            label="Returned",
            value=Decimal(returns),
            color=COLORS["returned"]
        ))
    
    return InventoryChartData(
        title="Inventory Status",
        segments=segments,
        total=initial_stock
    )


def build_cost_breakdown_chart(costs: CostMetrics) -> List[ChartDataPoint]:
    """
    Build cost breakdown data for pie/donut chart.
    
    Shows all cost components as segments.
    
    Args:
        costs: Cost metrics
        
    Returns:
        List of ChartDataPoint for cost breakdown visualization
    """
    segments = []
    
    # Only include non-zero costs
    if costs.product_cost > 0:
        segments.append(ChartDataPoint(
            label="Product Cost",
            value=costs.product_cost,
            color=COLORS["product_cost"]
        ))
    
    if costs.platform_fee > 0:
        segments.append(ChartDataPoint(
            label="Platform Fee",
            value=costs.platform_fee,
            color=COLORS["platform_fee"]
        ))
    
    if costs.shipping_total > 0:
        segments.append(ChartDataPoint(
            label="Shipping",
            value=costs.shipping_total,
            color=COLORS["shipping"]
        ))
    
    if costs.marketing_cost > 0:
        segments.append(ChartDataPoint(
            label="Marketing",
            value=costs.marketing_cost,
            color=COLORS["marketing"]
        ))
    
    return segments


def build_all_charts(
    product: ProductParameters,
    performance: PerformanceSignals,
    revenue: RevenueMetrics,
    costs: CostMetrics,
    profit: ProfitMetrics
) -> ChartsData:
    """
    Master function to build all chart data.
    
    This is the main entry point for the charts module.
    
    Args:
        product: Product parameters
        performance: Performance signals
        revenue: Revenue metrics
        costs: Cost metrics
        profit: Profit metrics
        
    Returns:
        ChartsData containing all chart structures
    """
    return ChartsData(
        revenue_breakdown=build_revenue_chart(revenue, costs, profit),
        sales_funnel=build_funnel_chart(performance, revenue),
        inventory_status=build_inventory_chart(product, revenue),
        cost_breakdown=build_cost_breakdown_chart(costs)
    )
