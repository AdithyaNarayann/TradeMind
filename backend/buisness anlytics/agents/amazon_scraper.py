"""
AGENT 2: Amazon Scraper Agent
Purpose: Autonomous scraping of Amazon search results
Type: Autonomous execution agent with stopping logic
Scope: SEARCH RESULTS ONLY (no product detail pages)
"""
import time
import random
import logging
from typing import List, Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from models.schemas import ProductData

logger = logging.getLogger(__name__)


class AmazonScraperAgent:
    """
    Autonomous Amazon search scraper with intelligent stopping logic
    """
    
    # Configuration
    BASE_URL = "https://www.amazon.in"
    MIN_PRODUCTS = 15  # Minimum before considering stopping
    TARGET_PRODUCTS = 25  # Ideal number
    MAX_PAGES = 2  # Safety limit
    MIN_DELAY = 4  # Seconds between requests
    MAX_DELAY = 8
    
    # Data quality thresholds
    MIN_REVIEWS = 10  # Products with fewer reviews are filtered
    MIN_VALID_RATIO = 0.6  # If <60% of products are valid, stop
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        
    def scrape_search_results(self, search_query: str) -> List[ProductData]:
        """
        Autonomously scrape Amazon search results
        
        Args:
            search_query: Optimized search query from Query Builder
            
        Returns:
            List of ProductData objects
        """
        logger.info(f"Starting scrape for query: '{search_query}'")
        
        all_products = []
        page_num = 1
        
        while True:
            # Check stopping conditions
            if self._should_stop_scraping(all_products, page_num):
                logger.info(f"Stopping scrape. Collected {len(all_products)} products")
                break
            
            # Scrape one page
            try:
                products = self._scrape_single_page(search_query, page_num)
                
                if not products:
                    logger.warning(f"No products found on page {page_num}")
                    break
                
                # Check data quality
                valid_products = [p for p in products if self._is_valid_product(p)]
                quality_ratio = len(valid_products) / len(products) if products else 0
                
                logger.info(
                    f"Page {page_num}: {len(products)} total, "
                    f"{len(valid_products)} valid ({quality_ratio:.1%})"
                )
                
                # If quality is too low, stop
                if quality_ratio < self.MIN_VALID_RATIO:
                    logger.warning(f"Data quality dropped to {quality_ratio:.1%}, stopping")
                    break
                
                all_products.extend(valid_products)
                page_num += 1
                
                # Random delay to appear human
                delay = random.uniform(self.MIN_DELAY, self.MAX_DELAY)
                logger.debug(f"Waiting {delay:.1f}s before next page")
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {e}")
                break
        
        # Final validation
        final_products = self._deduplicate_products(all_products)
        logger.info(f"Scrape complete: {len(final_products)} unique products")
        
        return final_products
    
    def _should_stop_scraping(self, products: List[ProductData], page_num: int) -> bool:
        """
        Agentic decision: Should we stop scraping?
        
        Returns:
            True if should stop, False if should continue
        """
        # Safety: Never exceed max pages
        if page_num > self.MAX_PAGES:
            return True
        
        # If we have enough products, stop
        if len(products) >= self.TARGET_PRODUCTS:
            return True
        
        # First page always runs
        if page_num == 1:
            return False
        
        # If we have minimum products and already scraped 2 pages, stop
        if len(products) >= self.MIN_PRODUCTS and page_num > 2:
            return True
        
        return False
    
    def _scrape_single_page(self, query: str, page: int) -> List[ProductData]:
        """Scrape one search results page"""
        url = self._build_search_url(query, page)
        
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            products = self._parse_search_results(soup)
            
            return products
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return []
    
    def _build_search_url(self, query: str, page: int) -> str:
        """Build Amazon search URL"""
        encoded_query = quote_plus(query)
        
        if page == 1:
            url = f"{self.BASE_URL}/s?k={encoded_query}"
        else:
            url = f"{self.BASE_URL}/s?k={encoded_query}&page={page}"
        
        return url
    
    def _parse_search_results(self, soup: BeautifulSoup) -> List[ProductData]:
        """Extract product data from search page"""
        products = []
        
        # Amazon uses specific selectors for product cards
        # This is a simplified version - real implementation needs careful selector engineering
        product_cards = soup.select('[data-component-type="s-search-result"]')
        
        for card in product_cards:
            try:
                product = self._extract_product_info(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.debug(f"Failed to parse product card: {e}")
                continue
        
        return products
    
    def _extract_product_info(self, card) -> Optional[ProductData]:
        """Extract info from a single product card"""
        try:
            # Title
            title_elem = card.select_one('h2 a span')
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            
            # Price (handle multiple formats)
            price = None
            price_elem = card.select_one('.a-price .a-offscreen')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extract number from "₹1,999" or "₹1,999.00"
                price_str = price_text.replace('₹', '').replace(',', '').strip()
                try:
                    price = float(price_str)
                except ValueError:
                    pass
            
            if not price or price <= 0:
                return None
            
            # Rating
            rating = None
            rating_elem = card.select_one('.a-icon-star-small .a-icon-alt')
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                try:
                    rating = float(rating_text.split()[0])
                except (ValueError, IndexError):
                    pass
            
            # Review count
            review_count = None
            review_elem = card.select_one('span[aria-label*="ratings"]')
            if review_elem:
                review_text = review_elem.get('aria-label', '')
                try:
                    # Extract number from "1,234 ratings"
                    review_count = int(review_text.replace(',', '').split()[0])
                except (ValueError, IndexError):
                    pass
            
            # URL
            url = ""
            url_elem = card.select_one('h2 a')
            if url_elem and url_elem.get('href'):
                url = self.BASE_URL + url_elem['href']
            
            return ProductData(
                title=title,
                price=price,
                rating=rating,
                review_count=review_count,
                url=url
            )
            
        except Exception as e:
            logger.debug(f"Product extraction failed: {e}")
            return None
    
    def _is_valid_product(self, product: ProductData) -> bool:
        """
        Validate if product data is good enough
        
        Returns:
            True if product should be kept
        """
        # Must have price
        if not product.price or product.price <= 0:
            return False
        
        # Must have minimum reviews for reliability
        if product.review_count is None or product.review_count < self.MIN_REVIEWS:
            return False
        
        # Title should be reasonable
        if not product.title or len(product.title) < 10:
            return False
        
        return True
    
    def _deduplicate_products(self, products: List[ProductData]) -> List[ProductData]:
        """Remove duplicate products based on URL or title similarity"""
        seen_urls = set()
        unique_products = []
        
        for product in products:
            # Use URL as unique identifier
            if product.url and product.url not in seen_urls:
                seen_urls.add(product.url)
                unique_products.append(product)
        
        return unique_products


# ===== USAGE EXAMPLE =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    scraper = AmazonScraperAgent()
    
    # Test scrape
    query = "boat wireless earbuds bluetooth"
    products = scraper.scrape_search_results(query)
    
    print(f"\nScraped {len(products)} products:")
    for i, p in enumerate(products[:5], 1):
        print(f"{i}. {p.title[:60]}... - ₹{p.price} ({p.review_count} reviews)")
