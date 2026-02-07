"""
Competitive Intelligence - Multi-Source Web Scraper

Scrapes multiple publicly-accessible sources for competitor pricing data:
  1. Amazon.in  - search results page
  2. Flipkart   - search results page
  3. Google Shopping (lite) - public search snippets

GRACEFUL DEGRADATION:
- Each source is independent; if one fails, others still return data
- If ALL sources fail, returns empty list (comparison engine handles it)
- Conservative timeouts per source (8s) so total stays under 25s

ETHICAL SCRAPING:
- Only public search result pages (no login, no API abuse)
- Single page per source (no pagination crawling)
- Respectful user-agent, no CAPTCHA solving
"""

import logging
import random
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# ── Shared helpers ────────────────────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def _ua() -> str:
    return random.choice(_USER_AGENTS)


def _headers(extra: dict | None = None) -> dict:
    h = {
        "User-Agent": _ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    if extra:
        h.update(extra)
    return h


def _safe_float(text: str | None) -> Optional[float]:
    """Extract a float from price-like text.  Returns None on failure."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        v = float(cleaned)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _safe_int(text: str | None) -> Optional[int]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d]", "", text.replace(",", ""))
    try:
        return int(cleaned)
    except (ValueError, TypeError):
        return None


# ══════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════

def scrape_competitor_data(
    product_name: str,
    category: Optional[str] = None,
    max_results: int = 20,
    product_description: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Scrape multiple sources in parallel and merge results.

    Returns list of raw product dicts:
        { title, price, rating, review_count, availability, source }
    """
    max_results = min(max_results, 30)
    query = f"{category} {product_name}" if category else product_name

    # Run scrapers concurrently with a short overall deadline
    scrapers = {
        "amazon_in":  (_scrape_amazon, query, max_results),
        "flipkart":   (_scrape_flipkart, query, max_results),
    }

    all_products: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(fn, q, n): name
            for name, (fn, q, n) in scrapers.items()
        }
        for future in as_completed(futures, timeout=20):
            source = futures[future]
            try:
                results = future.result()
                for p in results:
                    p["source"] = source
                all_products.extend(results)
                logger.info(f"Scraper [{source}]: {len(results)} products")
            except Exception as e:
                logger.warning(f"Scraper [{source}] failed: {e}")

    logger.info(f"Scraper total: {len(all_products)} products from all sources")
    return all_products


# ══════════════════════════════════════════════════════════════════
#  Amazon.in
# ══════════════════════════════════════════════════════════════════

def _scrape_amazon(query: str, max_results: int) -> List[Dict[str, Any]]:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    url = f"https://www.amazon.in/s?k={quote_plus(query)}"
    resp = requests.get(url, headers=_headers(), timeout=8, allow_redirects=True)
    if resp.status_code != 200:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select('[data-component-type="s-search-result"]')
    if not cards:
        cards = soup.select('.s-result-item[data-asin]')

    products = []
    for card in cards[:max_results]:
        p = _parse_amazon_card(card)
        if p and p.get("price"):
            products.append(p)
    return products


def _parse_amazon_card(card) -> Optional[Dict[str, Any]]:
    try:
        title_el = card.select_one('h2 a span') or card.select_one('h2 span') or card.select_one('.a-text-normal')
        title = title_el.get_text(strip=True) if title_el else None
        if not title:
            return None

        price_el = card.select_one('.a-price-whole')
        price = _safe_float(price_el.get_text(strip=True)) if price_el else None
        if not price:
            return None

        rating = None
        rating_el = card.select_one('.a-icon-star-small .a-icon-alt') or card.select_one('[aria-label*="out of 5"]')
        if rating_el:
            try:
                rating = float(rating_el.get_text(strip=True).split()[0])
            except (ValueError, IndexError):
                pass

        review_count = None
        review_el = card.select_one('a[href*="customerReviews"] span') or card.select_one('.a-size-base.s-underline-text')
        if review_el:
            review_count = _safe_int(review_el.get_text(strip=True))

        avail_el = card.select_one('.a-color-price') or card.select_one('.a-color-success')
        availability = avail_el.get_text(strip=True)[:50] if avail_el else "In Stock"

        return {"title": title, "price": price, "rating": rating,
                "review_count": review_count, "availability": availability}
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════
#  Flipkart
# ══════════════════════════════════════════════════════════════════

def _scrape_flipkart(query: str, max_results: int) -> List[Dict[str, Any]]:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    url = f"https://www.flipkart.com/search?q={quote_plus(query)}"
    resp = requests.get(url, headers=_headers(), timeout=8, allow_redirects=True)
    if resp.status_code != 200:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Flipkart uses various class patterns – try common ones
    cards = soup.select('div[data-id]')           # product grid cards
    if not cards:
        cards = soup.select('._1AtVbE')           # older layout
    if not cards:
        cards = soup.select('.tUxRFH')             # newer layout (2024+)
    if not cards:
        cards = soup.select('[data-tkid]')         # alternative

    products = []
    for card in cards[:max_results]:
        p = _parse_flipkart_card(card)
        if p and p.get("price"):
            products.append(p)
    return products


def _parse_flipkart_card(card) -> Optional[Dict[str, Any]]:
    try:
        # Title – multiple possible selectors
        title_el = (
            card.select_one('a[title]') or
            card.select_one('.KzDlHZ') or        # 2024+ product title class
            card.select_one('._4rR01T') or       # older class
            card.select_one('.s1Q9rs') or
            card.select_one('.IRpwTa')
        )
        title = None
        if title_el:
            title = title_el.get("title") or title_el.get_text(strip=True)
        if not title:
            return None

        # Price
        price_el = (
            card.select_one('.Nx9bqj') or        # 2024+ price class
            card.select_one('._30jeq3') or       # older class
            card.select_one('._1_WHN1') or
            card.select_one('.hl05eU .Nx9bqj')
        )
        price = _safe_float(price_el.get_text(strip=True)) if price_el else None
        if not price:
            return None

        # Rating
        rating = None
        rating_el = (
            card.select_one('.XQDdHH') or        # 2024+ rating badge
            card.select_one('._3LWZlK') or       # older class
            card.select_one('.hGSR34')
        )
        if rating_el:
            try:
                rating = float(rating_el.get_text(strip=True))
            except (ValueError, TypeError):
                pass

        # Review / rating count
        review_count = None
        count_el = card.select_one('.Wphh3N span:last-child') or card.select_one('._2_R_DZ span')
        if count_el:
            txt = count_el.get_text(strip=True)
            # "1,234 Ratings" or "567 Reviews"
            review_count = _safe_int(txt)

        return {"title": title, "price": price, "rating": rating,
                "review_count": review_count, "availability": "In Stock"}
    except Exception:
        return None
