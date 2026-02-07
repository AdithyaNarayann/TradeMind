"""
Analytics Calculations - Pure Functions for Business Metrics

All calculation functions are stateless and deterministic.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple, Optional, List
from dataclasses import dataclass

from .schemas import (
    ProductParameters,
    PerformanceSignals,
    BarChartData,
    FunnelChartData,
    FunnelStage,
    InventoryChartData,
    ChartDataPoint,
    ChartsData,
)


# =============================================================================
# HELPERS
# =============================================================================

def round_currency(value: Decimal, places: int = 2) -> Decimal:
    return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)


def safe_percentage(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return round_currency((numerator / denominator) * 100)


def safe_divide(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return round_currency(numerator / denominator)


# =============================================================================
# METRIC DATA CLASSES
# =============================================================================

@dataclass
class RevenueMetrics:
    gross_revenue: Decimal
    net_revenue: Decimal
    units_sold: int
    net_units_sold: int
    returns: int


@dataclass
class CostMetrics:
    product_cost: Decimal
    platform_fee: Decimal
    shipping_total: Decimal
    marketing_cost: Decimal
    total_cost: Decimal


@dataclass
class ProfitMetrics:
    profit_or_loss: Decimal
    profit_status: str
    profit_margin_percent: Decimal


@dataclass
class PerformanceRatios:
    conversion_rate: Decimal
    sell_through_rate: Decimal
    return_rate: Decimal
    roi: Optional[Decimal]


@dataclass
class UnitEconomics:
    profit_per_unit: Decimal
    effective_selling_price: Decimal


# =============================================================================
# CALCULATIONS
# =============================================================================

def calculate_revenue(product: ProductParameters, performance: PerformanceSignals) -> RevenueMetrics:
    units_sold = performance.units_sold
    returns = performance.returns
    net_units_sold = units_sold - returns
    
    gross_revenue = round_currency(Decimal(units_sold) * product.selling_price)
    net_revenue = round_currency(Decimal(net_units_sold) * product.selling_price)
    
    return RevenueMetrics(
        gross_revenue=gross_revenue,
        net_revenue=net_revenue,
        units_sold=units_sold,
        net_units_sold=net_units_sold,
        returns=returns
    )


def calculate_costs(product: ProductParameters, revenue: RevenueMetrics) -> CostMetrics:
    net_units = revenue.net_units_sold
    
    product_cost = round_currency(product.cost_price * Decimal(net_units))
    platform_fee = round_currency(revenue.gross_revenue * (product.platform_fee_percent / 100))
    shipping_total = round_currency(product.shipping_cost * Decimal(net_units))
    marketing_cost = round_currency(product.marketing_cost)
    total_cost = round_currency(product_cost + platform_fee + shipping_total + marketing_cost)
    
    return CostMetrics(
        product_cost=product_cost,
        platform_fee=platform_fee,
        shipping_total=shipping_total,
        marketing_cost=marketing_cost,
        total_cost=total_cost
    )


def calculate_profit_metrics(revenue: RevenueMetrics, costs: CostMetrics) -> ProfitMetrics:
    profit_or_loss = round_currency(revenue.net_revenue - costs.total_cost)
    
    if profit_or_loss > 0:
        profit_status = "PROFIT"
    elif profit_or_loss < 0:
        profit_status = "LOSS"
    else:
        profit_status = "BREAK_EVEN"
    
    profit_margin_percent = safe_percentage(profit_or_loss, revenue.net_revenue)
    
    return ProfitMetrics(
        profit_or_loss=profit_or_loss,
        profit_status=profit_status,
        profit_margin_percent=profit_margin_percent
    )


def calculate_performance_ratios(
    product: ProductParameters,
    performance: PerformanceSignals,
    revenue: RevenueMetrics,
    costs: CostMetrics,
    profit: ProfitMetrics
) -> PerformanceRatios:
    conversion_rate = safe_percentage(Decimal(performance.orders), Decimal(performance.chats))
    sell_through_rate = safe_percentage(Decimal(revenue.units_sold), Decimal(product.initial_stock))
    return_rate = safe_percentage(Decimal(revenue.returns), Decimal(revenue.units_sold))
    
    roi = None
    if costs.marketing_cost > 0:
        roi = safe_percentage(profit.profit_or_loss, costs.marketing_cost)
    
    return PerformanceRatios(
        conversion_rate=conversion_rate,
        sell_through_rate=sell_through_rate,
        return_rate=return_rate,
        roi=roi
    )


def calculate_unit_economics(
    product: ProductParameters,
    revenue: RevenueMetrics,
    profit: ProfitMetrics
) -> UnitEconomics:
    profit_per_unit = safe_divide(profit.profit_or_loss, Decimal(revenue.net_units_sold))
    platform_fee_per_unit = round_currency(product.selling_price * (product.platform_fee_percent / 100))
    effective_selling_price = round_currency(product.selling_price - platform_fee_per_unit)
    
    return UnitEconomics(
        profit_per_unit=profit_per_unit,
        effective_selling_price=effective_selling_price
    )


def calculate_all_metrics(
    product: ProductParameters,
    performance: PerformanceSignals
) -> Tuple[RevenueMetrics, CostMetrics, ProfitMetrics, PerformanceRatios, UnitEconomics, int]:
    revenue = calculate_revenue(product, performance)
    costs = calculate_costs(product, revenue)
    profit = calculate_profit_metrics(revenue, costs)
    ratios = calculate_performance_ratios(product, performance, revenue, costs, profit)
    unit_econ = calculate_unit_economics(product, revenue, profit)
    remaining_stock = product.initial_stock - revenue.net_units_sold
    
    return revenue, costs, profit, ratios, unit_econ, remaining_stock


# =============================================================================
# CHART BUILDERS
# =============================================================================

COLORS = {
    "revenue": "#22c55e",
    "cost": "#ef4444",
    "profit": "#3b82f6",
    "loss": "#f97316",
    "product_cost": "#8b5cf6",
    "platform_fee": "#ec4899",
    "shipping": "#f59e0b",
    "marketing": "#06b6d4",
    "sold": "#22c55e",
    "remaining": "#3b82f6",
    "returned": "#ef4444",
    "chats": "#6366f1",
    "orders": "#8b5cf6",
    "units": "#22c55e",
}


def build_revenue_chart(revenue: RevenueMetrics, costs: CostMetrics, profit: ProfitMetrics) -> BarChartData:
    profit_color = COLORS["profit"] if profit.profit_or_loss >= 0 else COLORS["loss"]
    
    return BarChartData(
        title="Revenue vs Cost vs Profit",
        labels=["Revenue", "Total Cost", "Profit/Loss"],
        datasets=[{
            "label": "Amount",
            "data": [float(revenue.net_revenue), float(costs.total_cost), float(profit.profit_or_loss)],
            "backgroundColor": [COLORS["revenue"], COLORS["cost"], profit_color],
            "borderColor": [COLORS["revenue"], COLORS["cost"], profit_color],
            "borderWidth": 1
        }]
    )


def build_funnel_chart(performance: PerformanceSignals, revenue: RevenueMetrics) -> FunnelChartData:
    chats = performance.chats
    orders = performance.orders
    units_sold = revenue.units_sold
    net_units = revenue.net_units_sold
    
    # All percentages relative to top of funnel (chats) for proper funnel visualization
    top = Decimal(chats) if chats > 0 else Decimal("1")
    
    stages = [
        FunnelStage(stage="Inquiries", value=chats, percentage=Decimal("100.00"), color=COLORS["chats"]),
        FunnelStage(stage="Orders", value=orders, 
                    percentage=min(safe_percentage(Decimal(orders), top), Decimal("100.00")),
                    color=COLORS["orders"]),
        FunnelStage(stage="Units Sold", value=units_sold,
                    percentage=min(safe_percentage(Decimal(units_sold), top), Decimal("100.00")),
                    color=COLORS["units"]),
        FunnelStage(stage="Net Sales", value=net_units,
                    percentage=min(safe_percentage(Decimal(net_units), top), Decimal("100.00")),
                    color=COLORS["sold"]),
    ]
    
    return FunnelChartData(title="Sales Funnel", stages=stages)


def build_inventory_chart(product: ProductParameters, revenue: RevenueMetrics) -> InventoryChartData:
    net_sold = revenue.net_units_sold
    returns = revenue.returns
    remaining = product.initial_stock - net_sold
    
    segments = [
        ChartDataPoint(label="Sold", value=Decimal(net_sold), color=COLORS["sold"]),
        ChartDataPoint(label="Remaining", value=Decimal(remaining), color=COLORS["remaining"]),
    ]
    
    if returns > 0:
        segments.append(ChartDataPoint(label="Returned", value=Decimal(returns), color=COLORS["returned"]))
    
    return InventoryChartData(title="Inventory Status", segments=segments, total=product.initial_stock)


def build_cost_breakdown_chart(costs: CostMetrics) -> List[ChartDataPoint]:
    segments = []
    if costs.product_cost > 0:
        segments.append(ChartDataPoint(label="Product Cost", value=costs.product_cost, color=COLORS["product_cost"]))
    if costs.platform_fee > 0:
        segments.append(ChartDataPoint(label="Platform Fee", value=costs.platform_fee, color=COLORS["platform_fee"]))
    if costs.shipping_total > 0:
        segments.append(ChartDataPoint(label="Shipping", value=costs.shipping_total, color=COLORS["shipping"]))
    if costs.marketing_cost > 0:
        segments.append(ChartDataPoint(label="Marketing", value=costs.marketing_cost, color=COLORS["marketing"]))
    return segments


def build_all_charts(
    product: ProductParameters,
    performance: PerformanceSignals,
    revenue: RevenueMetrics,
    costs: CostMetrics,
    profit: ProfitMetrics
) -> ChartsData:
    return ChartsData(
        revenue_breakdown=build_revenue_chart(revenue, costs, profit),
        sales_funnel=build_funnel_chart(performance, revenue),
        inventory_status=build_inventory_chart(product, revenue),
        cost_breakdown=build_cost_breakdown_chart(costs)
    )
