"""
Competitive Intelligence - API Routes

Single endpoint: POST /analytics/competitive-analysis

DESIGN DECISIONS:
- Stateless: every request is independent
- Graceful fallback: if scraping fails, returns a response with
  empty competitor data and a data_quality warning insight
- Strict response schema via Pydantic
- No background tasks, no caching, no database
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException

from .schemas import (
    CompetitiveAnalysisRequest,
    CompetitiveAnalysisResponse,
    MarketSummary,
    MyPosition,
    CompetitorSample,
    CompetitiveInsight,
    CompetitiveMeta,
    InsightSeverity,
    NormalizedProduct,
)
from .scraper import scrape_competitor_data
from .normalizer import normalize_scraped_data
from .comparison import compute_market_summary, compute_my_position, select_competitor_sample
from .insights import generate_insights

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Competitive Intelligence"])


@router.post(
    "/competitive-analysis",
    response_model=CompetitiveAnalysisResponse,
    summary="Run competitive analysis for a product",
    description=(
        "Scrapes publicly accessible product listings, normalizes the data, "
        "computes market statistics, determines your competitive position, "
        "and generates actionable rule-based insights. "
        "If scraping fails, returns a graceful fallback response."
    ),
)
async def competitive_analysis(request: CompetitiveAnalysisRequest):
    """
    Pipeline:
    1. Scrape competitor data (may return empty list)
    2. Normalize raw data → clean NormalizedProduct objects
    3. Compute market summary statistics
    4. Compute seller's position vs market
    5. Select competitor sample for response
    6. Generate rule-based insights
    7. Build and return response
    """
    start_time = datetime.now(timezone.utc)
    
    logger.info(f"Competitive analysis request: product='{request.product_name}', "
                f"category='{request.category}', price={request.my_price}")
    
    # Validate price
    if request.my_price <= 0:
        raise HTTPException(
            status_code=422,
            detail="my_price must be a positive number"
        )
    
    # === STEP 1: Scrape ===
    raw_products = scrape_competitor_data(
        product_name=request.product_name,
        category=request.category,
        max_results=15
    )
    
    scraped_data_available = len(raw_products) > 0
    
    # === STEP 2: Normalize ===
    normalized: List[NormalizedProduct] = []
    if raw_products:
        normalized = normalize_scraped_data(raw_products, request.my_price)
    
    # === STEP 3: Market Summary ===
    market_summary_dict = compute_market_summary(normalized)
    
    # === STEP 4: My Position ===
    position_dict = compute_my_position(request.my_price, market_summary_dict, normalized)
    
    # === STEP 5: Competitor Sample ===
    sample_dicts = select_competitor_sample(normalized, request.my_price, max_sample=5)
    
    # === STEP 6: Insights ===
    insights = generate_insights(request.my_price, market_summary_dict, position_dict)
    
    # === STEP 7: Build Response ===
    elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
    
    response = CompetitiveAnalysisResponse(
        market_summary=MarketSummary(
            avg_market_price=market_summary_dict["avg_market_price"],
            min_price=market_summary_dict["min_price"],
            max_price=market_summary_dict["max_price"],
            median_price=market_summary_dict["median_price"],
            price_spread=market_summary_dict["price_spread"],
            avg_rating=market_summary_dict["avg_rating"],
            competitor_count=market_summary_dict["competitor_count"],
        ),
        my_position=MyPosition(
            price_vs_market_avg_percent=position_dict["price_vs_market_avg_percent"],
            price_vs_median_percent=position_dict["price_vs_median_percent"],
            position=position_dict["position"],
            price_difference=position_dict["price_difference"],
            rank_estimate=position_dict["rank_estimate"],
        ),
        competitor_sample=[
            CompetitorSample(**s) for s in sample_dicts
        ],
        insights=insights,
        meta=CompetitiveMeta(
            scraped_data_available=scraped_data_available,
            competitor_count=market_summary_dict["competitor_count"],
            safe_to_cache=scraped_data_available and len(normalized) >= 3,
            data_source="amazon_in" if scraped_data_available else "none",
            scrape_timestamp=start_time.isoformat(),
            fallback_reason=None if scraped_data_available else "Scraping returned no results",
        ),
    )
    
    logger.info(f"Competitive analysis complete: {len(normalized)} products, "
                f"{len(insights)} insights, {elapsed_ms}ms")
    
    return response


@router.get(
    "/competitive-analysis/health",
    summary="Health check for competitive intelligence module",
)
async def competitive_health():
    return {
        "status": "healthy",
        "module": "competitive_intelligence",
        "version": "1.0.0",
    }
