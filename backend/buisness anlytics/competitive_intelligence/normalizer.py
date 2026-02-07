"""
Competitive Intelligence - Data Normalizer

Converts raw scraped data into clean, validated NormalizedProduct objects.

DESIGN DECISIONS:
- Strict validation via Pydantic
- Outlier filtering (removes absurd prices)
- Title cleaning (removes excessive whitespace, HTML artifacts)
- All functions are pure - no side effects

This layer sits between the scraper (messy web data)
and the comparison engine (needs clean, consistent data).
"""

import logging
import re
from typing import List, Dict, Any, Optional

from .schemas import NormalizedProduct

logger = logging.getLogger(__name__)


def normalize_scraped_data(
    raw_products: List[Dict[str, Any]],
    reference_price: float
) -> List[NormalizedProduct]:
    """
    Convert raw scraped product dicts into validated NormalizedProduct objects.
    
    Applies:
    1. Title cleaning
    2. Price validation and outlier removal
    3. Rating normalization
    4. Deduplication
    
    Args:
        raw_products: Raw dicts from scraper
        reference_price: Seller's price (used for outlier detection)
        
    Returns:
        List of clean NormalizedProduct objects
    """
    normalized = []
    seen_titles = set()  # For deduplication
    
    for raw in raw_products:
        product = _normalize_single(raw, reference_price)
        
        if product is None:
            continue
        
        # Deduplicate by cleaned title (case-insensitive)
        title_key = product.title.lower().strip()[:50]
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        
        normalized.append(product)
    
    logger.info(f"Normalizer: {len(raw_products)} raw → {len(normalized)} normalized products")
    return normalized


def _normalize_single(
    raw: Dict[str, Any],
    reference_price: float
) -> Optional[NormalizedProduct]:
    """
    Normalize a single raw product dict.
    
    Returns None if the product is invalid or an outlier.
    """
    try:
        # === TITLE ===
        title = raw.get("title")
        if not title or not isinstance(title, str):
            return None
        title = _clean_title(title)
        if len(title) < 3:
            return None
        
        # === PRICE ===
        price = raw.get("price")
        if price is None:
            return None
        
        try:
            price = float(price)
        except (ValueError, TypeError):
            return None
        
        if price <= 0:
            return None
        
        # Outlier detection: reject if price is >10x or <0.05x of reference
        # This catches "$1 accessories" and "$50,000 luxury items" in mixed results
        if reference_price > 0:
            ratio = price / reference_price
            if ratio > 10 or ratio < 0.05:
                logger.debug(f"Normalizer: Outlier rejected (ratio={ratio:.2f}): {title[:40]}")
                return None
        
        # === RATING ===
        rating = _normalize_rating(raw.get("rating"))
        
        # === REVIEW COUNT ===
        review_count = _normalize_review_count(raw.get("review_count"))
        
        # === AVAILABILITY ===
        availability = raw.get("availability")
        if availability and isinstance(availability, str):
            availability = availability.strip()[:50]
        else:
            availability = None
        
        return NormalizedProduct(
            title=title[:100],  # Truncate to 100 chars for display
            price=round(price, 2),
            rating=rating,
            review_count=review_count,
            availability=availability
        )
        
    except Exception as e:
        logger.debug(f"Normalizer: Failed to normalize product: {e}")
        return None


def _clean_title(title: str) -> str:
    """
    Clean a product title by removing noise.
    
    - Collapses whitespace
    - Removes leading/trailing junk
    - Strips HTML entity artifacts
    """
    # Collapse all whitespace (newlines, tabs, multiple spaces)
    title = re.sub(r'\s+', ' ', title).strip()
    
    # Remove common HTML entity artifacts
    title = title.replace("&amp;", "&")
    title = title.replace("&quot;", '"')
    title = title.replace("&#39;", "'")
    
    return title


def _normalize_rating(rating_raw: Any) -> Optional[float]:
    """Normalize rating to a float between 0 and 5, or None."""
    if rating_raw is None:
        return None
    
    try:
        rating = float(rating_raw)
        if 0 <= rating <= 5:
            return round(rating, 1)
        return None
    except (ValueError, TypeError):
        return None


def _normalize_review_count(count_raw: Any) -> Optional[int]:
    """Normalize review count to a positive int, or None."""
    if count_raw is None:
        return None
    
    try:
        count = int(count_raw)
        return count if count >= 0 else None
    except (ValueError, TypeError):
        return None
