"""
Input Schemas - Strict Validation for Incoming Data

These schemas validate seller-provided parameters and bot-provided signals.
All fields are explicitly typed with sensible constraints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from decimal import Decimal


class ProductParameters(BaseModel):
    """
    Seller-defined product cost and pricing parameters.
    
    These are static inputs that define the product economics.
    All monetary values are in the seller's currency.
    """
    
    cost_price: Decimal = Field(
        ...,
        gt=0,
        description="Cost to acquire/produce one unit"
    )
    selling_price: Decimal = Field(
        ...,
        gt=0,
        description="Price at which the product is sold"
    )
    initial_stock: int = Field(
        ...,
        ge=0,
        description="Total units available for sale"
    )
    platform_fee_percent: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=100,
        description="Platform commission as percentage (0-100)"
    )
    shipping_cost: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Shipping cost per unit"
    )
    marketing_cost: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Total marketing spend for this product"
    )
    
    @field_validator("selling_price")
    @classmethod
    def selling_price_reasonable(cls, v: Decimal) -> Decimal:
        """Warn-level validation: selling price should be positive."""
        if v <= 0:
            raise ValueError("selling_price must be greater than 0")
        return v


class PerformanceSignals(BaseModel):
    """
    Bot-provided live performance metrics.
    
    These are dynamic signals from negotiation/sales activity.
    Used to compute conversion rates and throughput.
    """
    
    chats: int = Field(
        default=0,
        ge=0,
        description="Total customer chat sessions / inquiries"
    )
    orders: int = Field(
        default=0,
        ge=0,
        description="Number of successful orders placed"
    )
    units_sold: int = Field(
        default=0,
        ge=0,
        description="Total units sold across all orders"
    )
    returns: int = Field(
        default=0,
        ge=0,
        description="Number of units returned (optional)"
    )
    
    @field_validator("returns")
    @classmethod
    def returns_cannot_exceed_sold(cls, v: int, info) -> int:
        """Returns cannot exceed units sold."""
        units_sold = info.data.get("units_sold", 0)
        if v > units_sold:
            raise ValueError("returns cannot exceed units_sold")
        return v


class AnalyticsRequest(BaseModel):
    """
    Complete analytics calculation request.
    
    Combines product economics with performance signals.
    This is the single input schema for the /analytics/calculate endpoint.
    """
    
    product: ProductParameters = Field(
        ...,
        description="Product cost and pricing parameters"
    )
    performance: PerformanceSignals = Field(
        ...,
        description="Bot-provided sales performance signals"
    )
    
    # Optional context for future database integration
    seller_id: Optional[str] = Field(
        default=None,
        description="Optional seller identifier for future DB tracking"
    )
    product_id: Optional[str] = Field(
        default=None,
        description="Optional product identifier for future DB tracking"
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO timestamp for when these metrics were captured"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "product": {
                        "cost_price": 500,
                        "selling_price": 999,
                        "initial_stock": 100,
                        "platform_fee_percent": 10,
                        "shipping_cost": 50,
                        "marketing_cost": 5000
                    },
                    "performance": {
                        "chats": 150,
                        "orders": 45,
                        "units_sold": 52,
                        "returns": 3
                    }
                }
            ]
        }
    }
