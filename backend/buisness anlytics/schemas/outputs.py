"""
Output Schemas - Chart-Ready Response Structures

These schemas define the API response format.
Designed to be directly consumable by frontend chart libraries.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from decimal import Decimal
from enum import Enum


class ProfitStatus(str, Enum):
    """Profit/Loss status indicator."""
    PROFIT = "PROFIT"
    LOSS = "LOSS"
    BREAK_EVEN = "BREAK_EVEN"


class SummaryMetrics(BaseModel):
    """
    Key business metrics as scalar values.
    
    These are the "hero numbers" for summary cards.
    All monetary values are rounded to 2 decimal places.
    """
    
    # Revenue metrics
    gross_revenue: Decimal = Field(description="Total revenue from sales")
    net_revenue: Decimal = Field(description="Revenue after returns")
    
    # Cost breakdown
    product_cost: Decimal = Field(description="Total cost of goods sold")
    platform_fee: Decimal = Field(description="Platform commission amount")
    shipping_total: Decimal = Field(description="Total shipping costs")
    marketing_cost: Decimal = Field(description="Marketing spend")
    total_cost: Decimal = Field(description="Sum of all costs")
    
    # Profit metrics
    profit_or_loss: Decimal = Field(description="Net profit (positive) or loss (negative)")
    profit_status: ProfitStatus = Field(description="PROFIT, LOSS, or BREAK_EVEN")
    profit_margin_percent: Decimal = Field(description="Profit as percentage of revenue")
    
    # Performance ratios
    conversion_rate: Decimal = Field(description="Orders / Chats as percentage")
    sell_through_rate: Decimal = Field(description="Units sold / Initial stock as percentage")
    return_rate: Decimal = Field(description="Returns / Units sold as percentage")
    
    # ROI (if marketing cost exists)
    roi: Optional[Decimal] = Field(
        default=None,
        description="Return on marketing investment as percentage"
    )
    
    # Unit economics
    profit_per_unit: Decimal = Field(description="Average profit per unit sold")
    effective_selling_price: Decimal = Field(description="Selling price after platform fee")
    
    # Inventory
    remaining_stock: int = Field(description="Units remaining in inventory")
    net_units_sold: int = Field(description="Units sold minus returns")


class ChartDataPoint(BaseModel):
    """Generic data point for charts."""
    label: str
    value: Decimal
    color: Optional[str] = None


class BarChartData(BaseModel):
    """
    Bar chart data for revenue vs cost vs profit visualization.
    
    Format compatible with Chart.js, Recharts, etc.
    """
    
    title: str = "Revenue vs Cost vs Profit"
    labels: List[str] = Field(description="X-axis labels")
    datasets: List[dict] = Field(description="Chart datasets with values and colors")


class FunnelStage(BaseModel):
    """Single stage in the conversion funnel."""
    stage: str
    value: int
    percentage: Decimal = Field(description="Percentage of previous stage")
    color: str


class FunnelChartData(BaseModel):
    """
    Funnel chart data for conversion visualization.
    
    Shows: Chats → Orders → Units Sold → Net Sales (after returns)
    """
    
    title: str = "Sales Funnel"
    stages: List[FunnelStage]


class InventoryChartData(BaseModel):
    """
    Inventory status for pie/donut chart visualization.
    
    Shows stock allocation: Sold vs Remaining vs Returned
    """
    
    title: str = "Inventory Status"
    segments: List[ChartDataPoint]
    total: int = Field(description="Initial stock count")


class ChartsData(BaseModel):
    """
    Container for all chart data.
    
    Each chart is pre-formatted for direct frontend consumption.
    """
    
    revenue_breakdown: BarChartData
    sales_funnel: FunnelChartData
    inventory_status: InventoryChartData
    cost_breakdown: List[ChartDataPoint] = Field(
        description="Cost components for pie chart"
    )


class InsightSeverity(str, Enum):
    """Severity level for business insights."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SUCCESS = "success"


class BusinessInsight(BaseModel):
    """
    Single business insight with context.
    
    Human-readable insight with severity and actionability.
    """
    
    message: str = Field(description="Human-readable insight")
    severity: InsightSeverity = Field(description="Severity level")
    category: str = Field(description="Insight category (conversion, profit, inventory, etc.)")
    metric_value: Optional[Decimal] = Field(
        default=None,
        description="The metric value that triggered this insight"
    )
    threshold: Optional[Decimal] = Field(
        default=None,
        description="The threshold that was crossed"
    )


class AnalyticsMeta(BaseModel):
    """
    Metadata and flags about the analytics calculation.
    
    Used for frontend decisions and future features.
    """
    
    is_profitable: bool = Field(description="True if profit > 0")
    is_break_even: bool = Field(description="True if profit == 0")
    has_marketing_data: bool = Field(description="True if marketing_cost > 0")
    has_sufficient_data: bool = Field(
        description="True if there's enough sales data for meaningful analysis"
    )
    simulation_ready: bool = Field(
        default=True,
        description="True if this response can be used for what-if simulations"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings about data quality"
    )


class AnalyticsResponse(BaseModel):
    """
    Complete analytics response.
    
    This is the single output schema for the /analytics/calculate endpoint.
    Structured for easy consumption by frontend dashboards.
    """
    
    summary_metrics: SummaryMetrics = Field(
        description="Key scalar metrics for summary cards"
    )
    charts: ChartsData = Field(
        description="Pre-formatted chart data"
    )
    insights: List[BusinessInsight] = Field(
        description="Rule-based business insights"
    )
    meta: AnalyticsMeta = Field(
        description="Metadata and flags"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary_metrics": {
                        "gross_revenue": 51948,
                        "net_revenue": 49449,
                        "product_cost": 26000,
                        "platform_fee": 5194.8,
                        "shipping_total": 2600,
                        "marketing_cost": 5000,
                        "total_cost": 38794.8,
                        "profit_or_loss": 10654.2,
                        "profit_status": "PROFIT",
                        "profit_margin_percent": 21.55,
                        "conversion_rate": 30.0,
                        "sell_through_rate": 52.0,
                        "return_rate": 5.77,
                        "roi": 213.08,
                        "profit_per_unit": 217.43,
                        "effective_selling_price": 899.1,
                        "remaining_stock": 48,
                        "net_units_sold": 49
                    },
                    "charts": "...(chart data)...",
                    "insights": [
                        {
                            "message": "Strong conversion rate of 30.0%",
                            "severity": "success",
                            "category": "conversion"
                        }
                    ],
                    "meta": {
                        "is_profitable": True,
                        "is_break_even": False,
                        "has_marketing_data": True,
                        "has_sufficient_data": True,
                        "simulation_ready": True,
                        "warnings": []
                    }
                }
            ]
        }
    }
