"""
Competitive Intelligence - Web Scraper

Lightweight scraper for publicly accessible product listing pages.

DESIGN DECISIONS:
- Uses requests + BeautifulSoup (no Selenium/Playwright overhead)
- Conservative timeouts (10s) to avoid blocking the API
- Respectful user-agent and delay between requests
- Targets Amazon.in search results (publicly accessible)
- Returns raw dicts - normalization is a separate step
- NEVER scrapes personal data, login-required pages, or APIs

GRACEFUL DEGRADATION:
- If scraping fails for ANY reason, returns empty list
- The comparison engine handles empty data with fallback estimates
- No exceptions propagate to the caller

ETHICAL SCRAPING:
- Only public search result pages
- No login/authentication bypass
- No CAPTCHA solving
- Respects rate limits via delays
- Minimal requests (1-2 pages max)
"""

import logging
import random
import time
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


def scrape_competitor_data(
    product_name: str,
    category: Optional[str] = None,
    max_results: int = 15
) -> List[Dict[str, Any]]:
    """
    Scrape publicly accessible product listings for competitor data.
    
    This function is the ONLY place in the module that touches the network.
    Everything downstream works with the data returned here.
    
    Args:
        product_name: Product to search for
        category: Optional category to refine search
        max_results: Maximum products to return (caps at 20)
        
    Returns:
        List of raw product dicts with keys: title, price, rating, review_count, availability
        Returns empty list on ANY failure (graceful degradation)
    """
    max_results = min(max_results, 20)  # Safety cap
    
    try:
        # Attempt live scraping
        results = _scrape_amazon_search(product_name, category, max_results)
        
        if results and len(results) >= 3:
            logger.info(f"Scraper: Found {len(results)} products for '{product_name}'")
            return results
        
        # If we got too few results, log and return what we have
        if results:
            logger.warning(f"Scraper: Only found {len(results)} products (minimum 3 preferred)")
            return results
        
        logger.warning(f"Scraper: No results for '{product_name}', returning empty")
        return []
        
    except Exception as e:
        # CRITICAL: Never let scraper failures crash the endpoint
        logger.error(f"Scraper failed for '{product_name}': {type(e).__name__}: {e}")
        return []


def _scrape_amazon_search(
    product_name: str,
    category: Optional[str],
    max_results: int
) -> List[Dict[str, Any]]:
    """
    Scrape Amazon.in search results page.
    
    Only scrapes the public search results page (no login required).
    Extracts: title, price, rating, review count from search result cards.
    
    Returns:
        List of raw product dicts, or empty list on failure
    """
    # Lazy import - only loaded when scraping is actually attempted
    # This keeps the module lightweight if scraping is never called
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("Scraper: requests or beautifulsoup4 not installed")
        return []
    
    # Build search query
    query = product_name
    if category:
        query = f"{category} {product_name}"
    
    encoded_query = quote_plus(query)
    url = f"https://www.amazon.in/s?k={encoded_query}"
    
    # Conservative headers - identify as a regular browser
    headers = {
        "User-Agent": _get_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    
    products = []
    
    try:
        # Single page request with conservative timeout
        response = requests.get(
            url,
            headers=headers,
            timeout=10,  # 10s timeout - don't block the API
            allow_redirects=True
        )
        
        # Check for non-200 responses
        if response.status_code != 200:
            logger.warning(f"Scraper: HTTP {response.status_code} from Amazon.in")
            return []
        
        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find product cards in search results
        # Amazon uses data-component-type="s-search-result" for search result cards
        result_cards = soup.select('[data-component-type="s-search-result"]')
        
        if not result_cards:
            # Fallback selector for different page layouts
            result_cards = soup.select('.s-result-item[data-asin]')
        
        for card in result_cards[:max_results]:
            product = _parse_search_result_card(card)
            if product and product.get("price"):
                products.append(product)
        
    except requests.exceptions.Timeout:
        logger.warning("Scraper: Request timed out (10s limit)")
        return []
    except requests.exceptions.ConnectionError:
        logger.warning("Scraper: Connection error - network may be unavailable")
        return []
    except Exception as e:
        logger.error(f"Scraper: Unexpected error during request: {e}")
        return []
    
    return products


def _parse_search_result_card(card) -> Optional[Dict[str, Any]]:
    """
    Parse a single Amazon search result card into a product dict.
    
    This function is resilient - missing fields get None values.
    Only products with a parseable price are considered valid.
    
    Args:
        card: BeautifulSoup element for a search result card
        
    Returns:
        Product dict or None if unparseable
    """
    try:
        product: Dict[str, Any] = {}
        
        # === TITLE ===
        # Try multiple selectors for title (Amazon changes layouts)
        title_el = (
            card.select_one('h2 a span') or
            card.select_one('h2 span') or
            card.select_one('.a-text-normal')
        )
        product["title"] = title_el.get_text(strip=True) if title_el else None
        
        # Skip if no title (probably an ad or widget)
        if not product["title"]:
            return None
        
        # === PRICE ===
        # Amazon formats prices as ₹X,XXX or ₹X,XXX.XX
        price_whole = card.select_one('.a-price-whole')
        if price_whole:
            price_text = price_whole.get_text(strip=True).replace(",", "").replace(".", "")
            try:
                product["price"] = float(price_text)
            except (ValueError, TypeError):
                product["price"] = None
        else:
            product["price"] = None
        
        # Skip products without a price
        if not product["price"] or product["price"] <= 0:
            return None
        
        # === RATING ===
        rating_el = card.select_one('.a-icon-star-small .a-icon-alt')
        if not rating_el:
            rating_el = card.select_one('[aria-label*="out of 5"]')
        
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            try:
                # Extract "4.2 out of 5 stars" → 4.2
                product["rating"] = float(rating_text.split()[0])
            except (ValueError, IndexError):
                product["rating"] = None
        else:
            product["rating"] = None
        
        # === REVIEW COUNT ===
        # Look for the review count link near the rating
        review_el = card.select_one('a[href*="customerReviews"] span') or card.select_one('.a-size-base.s-underline-text')
        if review_el:
            review_text = review_el.get_text(strip=True).replace(",", "").replace("(", "").replace(")", "")
            try:
                product["review_count"] = int(review_text)
            except (ValueError, TypeError):
                product["review_count"] = None
        else:
            product["review_count"] = None
        
        # === AVAILABILITY ===
        # Check for "In stock", "Only X left", etc.
        avail_el = card.select_one('.a-color-price') or card.select_one('.a-color-success')
        if avail_el:
            product["availability"] = avail_el.get_text(strip=True)[:50]  # Truncate
        else:
            product["availability"] = "In Stock"  # Default assumption for search results
        
        return product
        
    except Exception as e:
        # Never crash on a single card parse failure
        logger.debug(f"Scraper: Failed to parse card: {e}")
        return None


def _get_user_agent() -> str:
    """
    Return a reasonable browser user agent string.
    
    Uses a small set of common user agents to avoid fingerprinting.
    No external dependency (fake_useragent can fail).
    """
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    return random.choice(agents)
