"""
Business Metric Calculations - Pure Functions

All functions here are:
- Pure (same inputs always produce same outputs)
- Stateless (no external dependencies)
- Testable (easy to unit test in isolation)

These functions form the core calculation engine.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple, Optional
from dataclasses import dataclass

from schemas.inputs import ProductParameters, PerformanceSignals


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def round_currency(value: Decimal, places: int = 2) -> Decimal:
    """Round a decimal to specified places using banker's rounding."""
    return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)


def safe_percentage(numerator: Decimal, denominator: Decimal) -> Decimal:
    """Calculate percentage safely, returning 0 if denominator is 0."""
    if denominator == 0:
        return Decimal("0")
    return round_currency((numerator / denominator) * 100)


def safe_divide(numerator: Decimal, denominator: Decimal) -> Decimal:
    """Divide safely, returning 0 if denominator is 0."""
    if denominator == 0:
        return Decimal("0")
    return round_currency(numerator / denominator)


# =============================================================================
# DATA CLASSES FOR INTERMEDIATE RESULTS
# =============================================================================

@dataclass
class RevenueMetrics:
    """Revenue calculation results."""
    gross_revenue: Decimal
    net_revenue: Decimal
    units_sold: int
    net_units_sold: int
    returns: int


@dataclass
class CostMetrics:
    """Cost breakdown results."""
    product_cost: Decimal
    platform_fee: Decimal
    shipping_total: Decimal
    marketing_cost: Decimal
    total_cost: Decimal


@dataclass
class ProfitMetrics:
    """Profit calculation results."""
    profit_or_loss: Decimal
    profit_status: str  # "PROFIT", "LOSS", "BREAK_EVEN"
    profit_margin_percent: Decimal


@dataclass
class PerformanceRatios:
    """Performance ratio calculation results."""
    conversion_rate: Decimal
    sell_through_rate: Decimal
    return_rate: Decimal
    roi: Optional[Decimal]


@dataclass
class UnitEconomics:
    """Unit-level economics."""
    profit_per_unit: Decimal
    effective_selling_price: Decimal


# =============================================================================
# CORE CALCULATION FUNCTIONS
# =============================================================================

def calculate_revenue(
    product: ProductParameters,
    performance: PerformanceSignals
) -> RevenueMetrics:
    """
    Calculate revenue metrics from product parameters and performance signals.
    
    Revenue is based on units sold at selling price.
    Net revenue accounts for returns.
    
    Args:
        product: Product cost and pricing parameters
        performance: Sales performance signals
        
    Returns:
        RevenueMetrics with gross and net revenue figures
    """
    units_sold = performance.units_sold
    returns = performance.returns
    net_units_sold = units_sold - returns
    
    # Gross revenue = all units sold at selling price
    gross_revenue = round_currency(
        Decimal(units_sold) * product.selling_price
    )
    
    # Net revenue = net units (after returns) at selling price
    net_revenue = round_currency(
        Decimal(net_units_sold) * product.selling_price
    )
    
    return RevenueMetrics(
        gross_revenue=gross_revenue,
        net_revenue=net_revenue,
        units_sold=units_sold,
        net_units_sold=net_units_sold,
        returns=returns
    )


def calculate_costs(
    product: ProductParameters,
    revenue: RevenueMetrics
) -> CostMetrics:
    """
    Calculate all cost components.
    
    Costs are based on net units sold (returns don't incur full costs)
    Platform fee is calculated on gross revenue.
    
    Args:
        product: Product cost and pricing parameters
        revenue: Previously calculated revenue metrics
        
    Returns:
        CostMetrics with full cost breakdown
    """
    net_units = revenue.net_units_sold
    
    # Product cost = cost per unit * net units sold
    product_cost = round_currency(
        product.cost_price * Decimal(net_units)
    )
    
    # Platform fee = percentage of gross revenue
    # (Platforms typically charge on all sales, even if returned later)
    platform_fee = round_currency(
        revenue.gross_revenue * (product.platform_fee_percent / 100)
    )
    
    # Shipping = per unit * net units (assuming returns are picked up free)
    shipping_total = round_currency(
        product.shipping_cost * Decimal(net_units)
    )
    
    # Marketing is a fixed cost (sunk cost, not per-unit)
    marketing_cost = round_currency(product.marketing_cost)
    
    # Total cost
    total_cost = round_currency(
        product_cost + platform_fee + shipping_total + marketing_cost
    )
    
    return CostMetrics(
        product_cost=product_cost,
        platform_fee=platform_fee,
        shipping_total=shipping_total,
        marketing_cost=marketing_cost,
        total_cost=total_cost
    )


def calculate_profit_metrics(
    revenue: RevenueMetrics,
    costs: CostMetrics
) -> ProfitMetrics:
    """
    Calculate profit/loss and related metrics.
    
    Profit = Net Revenue - Total Costs
    Margin = Profit / Net Revenue * 100
    
    Args:
        revenue: Revenue metrics
        costs: Cost metrics
        
    Returns:
        ProfitMetrics with profit/loss figures and status
    """
    # Profit or loss
    profit_or_loss = round_currency(revenue.net_revenue - costs.total_cost)
    
    # Determine status
    if profit_or_loss > 0:
        profit_status = "PROFIT"
    elif profit_or_loss < 0:
        profit_status = "LOSS"
    else:
        profit_status = "BREAK_EVEN"
    
    # Profit margin percentage
    profit_margin_percent = safe_percentage(
        profit_or_loss,
        revenue.net_revenue
    )
    
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
    """
    Calculate performance ratios and ROI.
    
    Args:
        product: Product parameters (for initial stock)
        performance: Performance signals (for chats, orders)
        revenue: Revenue metrics
        costs: Cost metrics
        profit: Profit metrics
        
    Returns:
        PerformanceRatios with conversion, sell-through, and ROI
    """
    # Conversion rate = orders / chats * 100
    conversion_rate = safe_percentage(
        Decimal(performance.orders),
        Decimal(performance.chats)
    )
    
    # Sell-through rate = units sold / initial stock * 100
    sell_through_rate = safe_percentage(
        Decimal(revenue.units_sold),
        Decimal(product.initial_stock)
    )
    
    # Return rate = returns / units sold * 100
    return_rate = safe_percentage(
        Decimal(revenue.returns),
        Decimal(revenue.units_sold)
    )
    
    # ROI = (profit - marketing cost) / marketing cost * 100
    # Only calculate if marketing cost exists
    roi = None
    if costs.marketing_cost > 0:
        # ROI compares profit to marketing investment
        roi = safe_percentage(
            profit.profit_or_loss,
            costs.marketing_cost
        )
    
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
    """
    Calculate per-unit economics.
    
    Args:
        product: Product parameters
        revenue: Revenue metrics
        profit: Profit metrics
        
    Returns:
        UnitEconomics with per-unit profit and effective price
    """
    # Profit per unit = total profit / net units sold
    profit_per_unit = safe_divide(
        profit.profit_or_loss,
        Decimal(revenue.net_units_sold)
    )
    
    # Effective selling price = selling price - platform fee per unit
    platform_fee_per_unit = round_currency(
        product.selling_price * (product.platform_fee_percent / 100)
    )
    effective_selling_price = round_currency(
        product.selling_price - platform_fee_per_unit
    )
    
    return UnitEconomics(
        profit_per_unit=profit_per_unit,
        effective_selling_price=effective_selling_price
    )


def calculate_all_metrics(
    product: ProductParameters,
    performance: PerformanceSignals
) -> Tuple[RevenueMetrics, CostMetrics, ProfitMetrics, PerformanceRatios, UnitEconomics, int]:
    """
    Master calculation function that computes all metrics.
    
    This is the main entry point for the calculations module.
    It orchestrates all individual calculation functions.
    
    Args:
        product: Product cost and pricing parameters
        performance: Sales performance signals
        
    Returns:
        Tuple of all metric objects plus remaining stock
    """
    # Step 1: Revenue
    revenue = calculate_revenue(product, performance)
    
    # Step 2: Costs
    costs = calculate_costs(product, revenue)
    
    # Step 3: Profit
    profit = calculate_profit_metrics(revenue, costs)
    
    # Step 4: Performance ratios
    ratios = calculate_performance_ratios(
        product, performance, revenue, costs, profit
    )
    
    # Step 5: Unit economics
    unit_econ = calculate_unit_economics(product, revenue, profit)
    
    # Calculate remaining stock
    remaining_stock = product.initial_stock - revenue.net_units_sold
    
    return revenue, costs, profit, ratios, unit_econ, remaining_stock
