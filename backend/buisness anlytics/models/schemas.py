"""
Data models for the Amazon Pricing System
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ===== INPUT MODELS =====

class PriceRecommendationRequest(BaseModel):
    """Input from seller"""
    product_name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    specs: List[str] = Field(default_factory=list, description="Product specifications")
    base_price: float = Field(..., gt=0, description="Seller's base price")
    desired_margin: float = Field(..., ge=0, le=100, description="Desired profit margin %")


# ===== INTERMEDIATE MODELS =====

class ProductData(BaseModel):
    """Scraped product data"""
    title: str
    price: float
    rating: Optional[float] = None
    review_count: Optional[int] = None
    url: str


class CleanedMarketData(BaseModel):
    """Cleaned and validated market data"""
    clean_prices: List[float]
    median_price: float
    min_price: float
    max_price: float
    avg_price: float
    product_count: int


class PricingDecision(BaseModel):
    """Pricing strategy decision"""
    recommended_price: float
    strategy: Literal[
        "Competitive Entry Pricing",
        "Neutral Market Pricing", 
        "Premium Positioning",
        "Warning: Market Too Low"
    ]
    confidence: Literal["High", "Medium", "Low"]
    margin_achieved: float
    market_position: str  # e.g., "5% below median"


# ===== OUTPUT MODELS =====

class PriceRecommendationResponse(BaseModel):
    """Final response to seller"""
    success: bool
    
    # Core recommendation
    recommended_price: float
    strategy: str
    confidence: str
    
    # Market context
    market_median: float
    market_min: float
    market_max: float
    competitor_count: int
    
    # Business metrics
    margin_achieved: float
    market_position: str
    
    # Explainable insights
    insight: str
    reasoning: List[str]
    
    # Metadata
    timestamp: str
    query_used: str


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error_type: str
    message: str
    details: Optional[dict] = None
