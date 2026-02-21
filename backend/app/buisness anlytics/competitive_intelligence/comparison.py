"""
Competitive Intelligence - Market Comparison Engine

Pure computation module that takes normalized products and the seller's price,
then computes market-level statistics and the seller's competitive position.

DESIGN DECISIONS:
- All functions are pure (no I/O, no side effects)
- Handles edge cases: empty lists, single product, etc.
- Uses basic statistics (mean, median, min, max) - no numpy required
- Returns structured dicts ready for Pydantic model construction
"""

import logging
from statistics import mean, median
from typing import List, Dict, Any, Optional

from .schemas import NormalizedProduct

logger = logging.getLogger(__name__)


def compute_market_summary(
    products: List[NormalizedProduct]
) -> Dict[str, Any]:
    """
    Compute aggregate market statistics from normalized competitor products.
    
    Args:
        products: List of normalized competitor products
        
    Returns:
        Dict with keys: avg_market_price, min_price, max_price, median_price,
                        price_spread, avg_rating, competitor_count
        All floats are rounded to 2 decimal places.
    """
    if not products:
        return {
            "avg_market_price": 0.0,
            "min_price": 0.0,
            "max_price": 0.0,
            "median_price": 0.0,
            "price_spread": 0.0,
            "avg_rating": None,
            "competitor_count": 0,
        }
    
    prices = [p.price for p in products]
    ratings = [p.rating for p in products if p.rating is not None]
    
    avg_price = round(mean(prices), 2)
    min_price = round(min(prices), 2)
    max_price = round(max(prices), 2)
    median_price = round(median(prices), 2)
    
    # Price spread = max - min (absolute range)
    price_spread = round(max_price - min_price, 2)
    
    avg_rating = round(mean(ratings), 1) if ratings else None
    
    return {
        "avg_market_price": avg_price,
        "min_price": min_price,
        "max_price": max_price,
        "median_price": median_price,
        "price_spread": price_spread,
        "avg_rating": avg_rating,
        "competitor_count": len(products),
    }


def compute_my_position(
    my_price: float,
    market_summary: Dict[str, Any],
    products: List[NormalizedProduct]
) -> Dict[str, Any]:
    """
    Determine the seller's competitive position relative to the market.
    
    Args:
        my_price: The seller's current price
        market_summary: Output from compute_market_summary()
        products: Normalized competitor products (for rank calculation)
        
    Returns:
        Dict with keys: price_vs_market_avg_percent, position, price_difference,
                        rank_estimate, percentile
    """
    avg_price = market_summary.get("avg_market_price", 0)
    
    if avg_price <= 0 or not products:
        return {
            "price_vs_market_avg_percent": 0.0,
            "price_vs_median_percent": 0.0,
            "position": "unknown",
            "price_difference": 0.0,
            "rank_estimate": "N/A",
            "percentile": 50.0,
        }
    
    # How much above/below market average (negative = below avg = cheaper)
    price_diff = round(my_price - avg_price, 2)
    price_vs_avg_pct = round((price_diff / avg_price) * 100, 2)
    
    # How much above/below market median
    median_price = market_summary.get("median_price", avg_price)
    if median_price > 0:
        price_vs_median_pct = round(((my_price - median_price) / median_price) * 100, 2)
    else:
        price_vs_median_pct = 0.0
    
    # Position label
    if price_vs_avg_pct < -5:
        position = "below_market"
    elif price_vs_avg_pct > 5:
        position = "above_market"
    else:
        position = "at_market"
    
    # Rank estimate: where does my_price fall among competitor prices?
    # Rank 1 = cheapest
    prices_sorted = sorted([p.price for p in products])
    rank = 1
    for p in prices_sorted:
        if my_price > p:
            rank += 1
        else:
            break
    
    total = len(products) + 1  # Include the seller
    rank_label = _rank_to_label(rank, total)
    
    # Percentile: what % of competitors are priced above me?
    cheaper_count = sum(1 for p in products if p.price < my_price)
    percentile = round((cheaper_count / len(products)) * 100, 1) if products else 50.0
    
    return {
        "price_vs_market_avg_percent": price_vs_avg_pct,
        "price_vs_median_percent": price_vs_median_pct,
        "position": position,
        "price_difference": price_diff,
        "rank_estimate": rank_label,
        "percentile": percentile,
    }


def select_competitor_sample(
    products: List[NormalizedProduct],
    my_price: float,
    max_sample: int = 5
) -> List[Dict[str, Any]]:
    """
    Select a representative sample of competitors for the response.
    
    Strategy: pick cheapest, most expensive, and highest rated,
    then fill remaining slots with diversity picks.
    
    Args:
        products: Full list of normalized products
        my_price: Seller's price (for price_vs_mine calculation)
        max_sample: Maximum number to return (default 5)
        
    Returns:
        List of product dicts ready for CompetitorSample construction
    """
    if not products:
        return []
    
    if len(products) <= max_sample:
        return [_product_to_dict(p, my_price) for p in products]
    
    selected = []
    selected_indices = set()
    
    # Strategy picks
    strategies = [
        ("cheapest", lambda ps: min(range(len(ps)), key=lambda i: ps[i].price)),
        ("most_expensive", lambda ps: max(range(len(ps)), key=lambda i: ps[i].price)),
        ("highest_rated", lambda ps: max(
            range(len(ps)),
            key=lambda i: ps[i].rating if ps[i].rating else 0
        )),
    ]
    
    for name, selector in strategies:
        try:
            idx = selector(products)
            if idx not in selected_indices:
                selected.append(_product_to_dict(products[idx], my_price))
                selected_indices.add(idx)
        except (ValueError, IndexError):
            continue
    
    # Fill remaining slots with evenly spaced picks
    remaining_slots = max_sample - len(selected)
    if remaining_slots > 0:
        available = [i for i in range(len(products)) if i not in selected_indices]
        step = max(1, len(available) // (remaining_slots + 1))
        for i in range(0, len(available), step):
            if len(selected) >= max_sample:
                break
            selected.append(_product_to_dict(products[available[i]], my_price))
    
    return selected


def _rank_to_label(rank: int, total: int) -> str:
    """Convert numeric rank to a human-readable label."""
    if rank == 1:
        return "Cheapest"
    if rank == total:
        return "Most expensive"
    if rank == 2:
        return "2nd cheapest"
    if rank == 3:
        return "3rd cheapest"
    return f"{rank}th of {total}"


def _product_to_dict(product: NormalizedProduct, my_price: float) -> Dict[str, Any]:
    """Convert a NormalizedProduct to a plain dict for response construction."""
    price_vs_mine = round(((product.price - my_price) / my_price) * 100, 2) if my_price > 0 else 0.0
    return {
        "title": product.title,
        "price": product.price,
        "rating": product.rating,
        "review_count": product.review_count,
        "availability": product.availability,
        "price_vs_mine": price_vs_mine,
    }
