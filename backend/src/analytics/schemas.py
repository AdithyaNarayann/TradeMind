"""
Analytics Schemas - Input and Output Models

Pydantic models for the analytics engine.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from decimal import Decimal
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class ProfitStatus(str, Enum):
    """Profit/Loss status indicator."""
    PROFIT = "PROFIT"
    LOSS = "LOSS"
    BREAK_EVEN = "BREAK_EVEN"


class InsightSeverity(str, Enum):
    """Severity level for business insights."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SUCCESS = "success"


# =============================================================================
# INPUT SCHEMAS
# =============================================================================

class ProductParameters(BaseModel):
    """Seller-defined product cost and pricing parameters."""
    
    cost_price: Decimal = Field(..., gt=0, description="Cost to acquire/produce one unit")
    selling_price: Decimal = Field(..., gt=0, description="Price at which the product is sold")
    initial_stock: int = Field(..., ge=0, description="Total units available for sale")
    platform_fee_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100, description="Platform commission %")
    shipping_cost: Decimal = Field(default=Decimal("0"), ge=0, description="Shipping cost per unit")
    marketing_cost: Decimal = Field(default=Decimal("0"), ge=0, description="Total marketing spend")


class PerformanceSignals(BaseModel):
    """Bot-provided live performance metrics."""
    
    chats: int = Field(default=0, ge=0, description="Total customer inquiries")
    orders: int = Field(default=0, ge=0, description="Number of orders placed")
    units_sold: int = Field(default=0, ge=0, description="Total units sold")
    returns: int = Field(default=0, ge=0, description="Units returned")
    
    @field_validator("returns")
    @classmethod
    def returns_cannot_exceed_sold(cls, v: int, info) -> int:
        units_sold = info.data.get("units_sold", 0)
        if v > units_sold:
            raise ValueError("returns cannot exceed units_sold")
        return v


class AnalyticsRequest(BaseModel):
    """Complete analytics calculation request."""
    
    product: ProductParameters
    performance: PerformanceSignals
    seller_id: Optional[str] = None
    product_id: Optional[str] = None
    timestamp: Optional[str] = None


# =============================================================================
# OUTPUT SCHEMAS
# =============================================================================

class SummaryMetrics(BaseModel):
    """Key business metrics as scalar values."""
    
    gross_revenue: Decimal
    net_revenue: Decimal
    product_cost: Decimal
    platform_fee: Decimal
    shipping_total: Decimal
    marketing_cost: Decimal
    total_cost: Decimal
    profit_or_loss: Decimal
    profit_status: ProfitStatus
    profit_margin_percent: Decimal
    conversion_rate: Decimal
    sell_through_rate: Decimal
    return_rate: Decimal
    roi: Optional[Decimal] = None
    profit_per_unit: Decimal
    effective_selling_price: Decimal
    remaining_stock: int
    net_units_sold: int


class ChartDataPoint(BaseModel):
    """Generic data point for charts."""
    label: str
    value: Decimal
    color: Optional[str] = None


class BarChartData(BaseModel):
    """Bar chart data."""
    title: str = "Revenue vs Cost vs Profit"
    labels: List[str]
    datasets: List[dict]


class FunnelStage(BaseModel):
    """Single stage in the conversion funnel."""
    stage: str
    value: int
    percentage: Decimal
    color: str


class FunnelChartData(BaseModel):
    """Funnel chart data."""
    title: str = "Sales Funnel"
    stages: List[FunnelStage]


class InventoryChartData(BaseModel):
    """Inventory status chart data."""
    title: str = "Inventory Status"
    segments: List[ChartDataPoint]
    total: int


class ChartsData(BaseModel):
    """Container for all chart data."""
    revenue_breakdown: BarChartData
    sales_funnel: FunnelChartData
    inventory_status: InventoryChartData
    cost_breakdown: List[ChartDataPoint]


class BusinessInsight(BaseModel):
    """Single business insight with context."""
    message: str
    severity: InsightSeverity
    category: str
    metric_value: Optional[Decimal] = None
    threshold: Optional[Decimal] = None


class AnalyticsMeta(BaseModel):
    """Metadata about the analytics calculation."""
    is_profitable: bool
    is_break_even: bool
    has_marketing_data: bool
    has_sufficient_data: bool
    simulation_ready: bool = True
    warnings: List[str] = []


class AnalyticsResponse(BaseModel):
    """Complete analytics response."""
    summary_metrics: SummaryMetrics
    charts: ChartsData
    insights: List[BusinessInsight]
    meta: AnalyticsMeta
