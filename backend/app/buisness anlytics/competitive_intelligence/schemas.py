"""
Competitive Intelligence - Pydantic Schemas

Input validation and output structures for the competitive analysis endpoint.
Completely isolated from the existing analytics schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# =============================================================================
# INPUT SCHEMAS
# =============================================================================

class CompetitiveAnalysisRequest(BaseModel):
    """
    Input for competitive analysis.
    
    Product details drive web scraping + LLM analysis.
    """
    
    product_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Product name or search query to find competitors"
    )
    product_description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Detailed product description to help the AI understand features & positioning"
    )
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Product category for refined search (e.g., 'Electronics', 'Fashion')"
    )
    my_price: float = Field(
        ...,
        gt=0,
        description="Your selling price for this product"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "product_name": "Boat Airdopes 141 Wireless Earbuds",
                    "product_description": "True wireless earbuds with Bluetooth 5.1, 42H playback, IPX4 water resistance, ENx noise cancellation, dual mics",
                    "category": "Electronics",
                    "my_price": 1299
                }
            ]
        }
    }


# =============================================================================
# INTERNAL DATA STRUCTURES
# =============================================================================

class NormalizedProduct(BaseModel):
    """
    Standardized product structure after scraping and normalization.
    
    This is the internal format - raw scraped data is converted to this
    before any comparison or insight generation.
    """
    
    title: str = Field(description="Cleaned product title")
    price: float = Field(gt=0, description="Price in seller's currency")
    rating: Optional[float] = Field(default=None, ge=0, le=5, description="Rating out of 5")
    review_count: Optional[int] = Field(default=None, ge=0, description="Number of reviews")
    availability: Optional[str] = Field(default=None, description="Stock status")


# =============================================================================
# OUTPUT SCHEMAS
# =============================================================================

class MarketSummary(BaseModel):
    """
    Aggregate market statistics from competitor data.
    
    Provides a high-level view of the competitive landscape.
    """
    
    avg_market_price: float = Field(description="Average price across competitors")
    min_price: float = Field(description="Lowest competitor price found")
    max_price: float = Field(description="Highest competitor price found")
    median_price: float = Field(description="Median competitor price")
    avg_rating: Optional[float] = Field(default=None, description="Average competitor rating")
    competitor_count: int = Field(description="Number of competitors analyzed")
    price_spread: float = Field(description="Max - Min price (market price range)")


class MyPosition(BaseModel):
    """
    How the seller's price compares to the market.
    
    This is the core positioning output - tells the seller
    exactly where they stand relative to competitors.
    """
    
    price_vs_market_avg_percent: float = Field(
        description="% difference from market average (negative = cheaper, positive = more expensive)"
    )
    price_vs_median_percent: float = Field(
        description="% difference from market median"
    )
    position: str = Field(
        description="Market position label: 'below_market', 'at_market', 'above_market'"
    )
    price_difference: float = Field(
        description="Absolute difference from market average"
    )
    rank_estimate: str = Field(
        description="Estimated price rank (e.g., 'Cheapest', '2nd cheapest', 'Most expensive')"
    )


class CompetitorSample(BaseModel):
    """
    A sanitized competitor entry for display.
    
    No raw HTML, no personal data - just clean, structured product info.
    """
    
    title: str = Field(description="Product title (truncated to 100 chars)")
    price: float = Field(description="Listed price")
    rating: Optional[float] = Field(default=None, description="Rating if available")
    review_count: Optional[int] = Field(default=None, description="Review count if available")
    availability: Optional[str] = Field(default=None, description="Availability status")
    price_vs_mine: float = Field(description="% difference from my price")


class InsightSeverity(str, Enum):
    """Severity levels for competitive insights."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SUCCESS = "success"
    OPPORTUNITY = "opportunity"


class CompetitiveInsight(BaseModel):
    """
    A single competitive insight with context.
    
    Designed to be human-readable AND LLM-friendly.
    Each insight can be consumed by AI agents for further analysis.
    """
    
    message: str = Field(description="Human-readable insight text")
    severity: InsightSeverity = Field(description="Severity/type of insight")
    category: str = Field(description="Category: pricing, ratings, market, opportunity")
    data_point: Optional[float] = Field(default=None, description="The metric value behind the insight")


class LLMAnalysis(BaseModel):
    """
    AI-generated deep competitive analysis from OpenRouter / Gemini.
    """
    executive_summary: str = Field(default="", description="2-3 sentence competitive overview")
    pricing_strategy: str = Field(default="", description="Specific pricing recommendation")
    strengths: List[str] = Field(default_factory=list, description="Competitive strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Competitive weaknesses")
    opportunities: List[str] = Field(default_factory=list, description="Market opportunities")
    threats: List[str] = Field(default_factory=list, description="Competitive threats")
    recommended_price: Optional[float] = Field(default=None, description="AI-suggested optimal price")
    action_items: List[str] = Field(default_factory=list, description="Prioritised next steps")
    market_analysis: str = Field(default="", description="Paragraph-length deep dive")


class CompetitiveMeta(BaseModel):
    """
    Metadata about the analysis.
    
    Helps the frontend and AI agents understand data quality
    and caching decisions.
    """
    
    scraped_data_available: bool = Field(
        description="True if live scraped data was used (vs fallback)"
    )
    competitor_count: int = Field(
        description="Number of competitors found"
    )
    safe_to_cache: bool = Field(
        description="True if results are stable enough to cache (TTL: ~1 hour)"
    )
    data_source: str = Field(
        description="Where the data came from (e.g., 'amazon_in', 'fallback_estimate')"
    )
    scrape_timestamp: str = Field(
        description="ISO timestamp when data was fetched"
    )
    fallback_reason: Optional[str] = Field(
        default=None,
        description="If fallback was used, explains why"
    )
    sources_used: List[str] = Field(
        default_factory=list,
        description="Which scrapers returned data (e.g., ['amazon_in', 'flipkart'])"
    )
    llm_analysis_available: bool = Field(
        default=False,
        description="True if AI analysis was successfully generated"
    )


class CompetitiveAnalysisResponse(BaseModel):
    """
    Complete competitive analysis response.
    
    Structured for easy frontend consumption and AI agent integration.
    """
    
    market_summary: MarketSummary = Field(
        description="Aggregate market statistics"
    )
    my_position: MyPosition = Field(
        description="Seller's position relative to market"
    )
    competitor_sample: List[CompetitorSample] = Field(
        description="Top competitors (sanitized, max 10)"
    )
    insights: List[CompetitiveInsight] = Field(
        description="Rule-based competitive insights"
    )
    llm_analysis: Optional[LLMAnalysis] = Field(
        default=None,
        description="AI-generated deep competitive analysis (null if LLM unavailable)"
    )
    meta: CompetitiveMeta = Field(
        description="Analysis metadata and flags"
    )
