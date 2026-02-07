"""
AGENT 3: Data Cleaning & Validation Agent
Purpose: Clean scraped data and prepare analytics-ready dataset
Type: Rule-based intelligence agent
"""
import logging
from typing import List
import numpy as np

from models.schemas import ProductData, CleanedMarketData

logger = logging.getLogger(__name__)


class DataCleaningAgent:
    """
    Cleans and validates scraped product data
    This agent determines trustworthiness of outputs
    """
    
    # Outlier detection parameters
    IQR_MULTIPLIER = 2.5  # For outlier removal
    MIN_PRODUCTS_FOR_ANALYSIS = 5  # Minimum for statistical validity
    
    def __init__(self):
        pass
    
    def clean_and_validate(
        self,
        raw_products: List[ProductData],
        reference_price: float
    ) -> CleanedMarketData:
        """
        Clean scraped data and prepare for analysis
        
        Args:
            raw_products: Raw scraped products
            reference_price: Seller's base price for context
            
        Returns:
            CleanedMarketData with statistics
            
        Raises:
            ValueError: If data quality is too poor
        """
        logger.info(f"Cleaning {len(raw_products)} raw products")
        
        # Step 1: Basic filtering
        filtered = self._apply_basic_filters(raw_products)
        logger.info(f"After basic filters: {len(filtered)} products")
        
        if len(filtered) < self.MIN_PRODUCTS_FOR_ANALYSIS:
            raise ValueError(
                f"Insufficient data: only {len(filtered)} products after filtering. "
                f"Need at least {self.MIN_PRODUCTS_FOR_ANALYSIS}."
            )
        
        # Step 2: Extract prices
        prices = [p.price for p in filtered]
        
        # Step 3: Remove outliers
        clean_prices = self._remove_outliers(prices, reference_price)
        logger.info(f"After outlier removal: {len(clean_prices)} prices")
        
        if len(clean_prices) < self.MIN_PRODUCTS_FOR_ANALYSIS:
            raise ValueError(
                f"Too many outliers removed. Only {len(clean_prices)} prices remain."
            )
        
        # Step 4: Calculate statistics
        stats = self._calculate_statistics(clean_prices)
        
        # Step 5: Validate quality
        self._validate_data_quality(stats, reference_price)
        
        logger.info(
            f"Cleaned data ready: median=₹{stats.median_price:.2f}, "
            f"range=₹{stats.min_price:.2f}-₹{stats.max_price:.2f}"
        )
        
        return stats
    
    def _apply_basic_filters(self, products: List[ProductData]) -> List[ProductData]:
        """
        Apply basic filtering rules
        
        Removes:
        - Products with no price
        - Products with < 10 reviews
        - Products with suspiciously low prices (< ₹100)
        - Products with suspiciously high prices (> ₹1,00,000)
        """
        filtered = []
        
        for product in products:
            # Must have price
            if not product.price or product.price <= 0:
                continue
            
            # Must have minimum reviews (already filtered in scraper, but double-check)
            if not product.review_count or product.review_count < 10:
                continue
            
            # Reasonable price range (adjust based on category)
            if product.price < 100 or product.price > 100000:
                continue
            
            # Must have valid title
            if not product.title or len(product.title) < 10:
                continue
            
            filtered.append(product)
        
        return filtered
    
    def _remove_outliers(
        self,
        prices: List[float],
        reference_price: float
    ) -> List[float]:
        """
        Remove extreme outliers using IQR method with reference price context
        
        Args:
            prices: List of prices
            reference_price: Seller's price for additional context
            
        Returns:
            Cleaned price list
        """
        if len(prices) < 4:
            return prices
        
        prices_array = np.array(prices)
        
        # Calculate IQR
        q1 = np.percentile(prices_array, 25)
        q3 = np.percentile(prices_array, 75)
        iqr = q3 - q1
        
        # Define outlier bounds
        lower_bound = q1 - (self.IQR_MULTIPLIER * iqr)
        upper_bound = q3 + (self.IQR_MULTIPLIER * iqr)
        
        # Additional context: if reference price is way outside bounds,
        # expand bounds slightly to include similar products
        if reference_price < lower_bound:
            lower_bound = min(lower_bound, reference_price * 0.7)
        elif reference_price > upper_bound:
            upper_bound = max(upper_bound, reference_price * 1.3)
        
        # Filter outliers
        clean_prices = [
            p for p in prices
            if lower_bound <= p <= upper_bound
        ]
        
        # Log what was removed
        removed = len(prices) - len(clean_prices)
        if removed > 0:
            logger.info(
                f"Removed {removed} outliers. "
                f"Bounds: ₹{lower_bound:.2f} - ₹{upper_bound:.2f}"
            )
        
        return clean_prices
    
    def _calculate_statistics(self, prices: List[float]) -> CleanedMarketData:
        """Calculate market statistics"""
        prices_array = np.array(prices)
        
        return CleanedMarketData(
            clean_prices=prices,
            median_price=float(np.median(prices_array)),
            min_price=float(np.min(prices_array)),
            max_price=float(np.max(prices_array)),
            avg_price=float(np.mean(prices_array)),
            product_count=len(prices)
        )
    
    def _validate_data_quality(
        self,
        stats: CleanedMarketData,
        reference_price: float
    ) -> None:
        """
        Final validation of data quality
        
        Raises:
            ValueError: If data fails quality checks
        """
        # Check 1: Sufficient product count
        if stats.product_count < self.MIN_PRODUCTS_FOR_ANALYSIS:
            raise ValueError(
                f"Insufficient products: {stats.product_count} "
                f"(minimum: {self.MIN_PRODUCTS_FOR_ANALYSIS})"
            )
        
        # Check 2: Reasonable price range
        price_range = stats.max_price - stats.min_price
        median_range_ratio = price_range / stats.median_price if stats.median_price > 0 else 0
        
        if median_range_ratio > 5:  # Range is > 5x median
            logger.warning(
                f"Very wide price range detected: {median_range_ratio:.1f}x median. "
                "Results may be unreliable."
            )
        
        # Check 3: Median should be reasonable
        if stats.median_price < 100:
            raise ValueError(
                f"Median price too low (₹{stats.median_price:.2f}). "
                "Market data may be invalid."
            )
        
        # Check 4: Reference price shouldn't be wildly different from market
        if reference_price > 0:
            deviation = abs(reference_price - stats.median_price) / stats.median_price
            
            if deviation > 3:  # More than 3x different
                logger.warning(
                    f"Your price (₹{reference_price:.2f}) is {deviation:.1f}x "
                    f"different from market median (₹{stats.median_price:.2f}). "
                    "Verify product category."
                )
    
    def get_price_distribution(self, stats: CleanedMarketData) -> dict:
        """
        Get price distribution for analytics
        
        Returns:
            Dictionary with percentile breakdown
        """
        prices_array = np.array(stats.clean_prices)
        
        return {
            'p10': float(np.percentile(prices_array, 10)),
            'p25': float(np.percentile(prices_array, 25)),
            'p50': float(np.percentile(prices_array, 50)),
            'p75': float(np.percentile(prices_array, 75)),
            'p90': float(np.percentile(prices_array, 90)),
            'mean': stats.avg_price,
            'std': float(np.std(prices_array))
        }


# ===== USAGE EXAMPLE =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Mock data
    mock_products = [
        ProductData(title=f"Product {i}", price=p, rating=4.2, review_count=100, url="")
        for i, p in enumerate([
            1899, 1949, 1999, 2049, 2099, 2149, 2199, 
            1850, 1900, 1950, 2000, 2050, 2100,
            5000,  # Outlier
            500    # Outlier
        ])
    ]
    
    agent = DataCleaningAgent()
    
    try:
        cleaned = agent.clean_and_validate(mock_products, reference_price=1950)
        
        print(f"\nCleaned Market Data:")
        print(f"Products: {cleaned.product_count}")
        print(f"Median: ₹{cleaned.median_price:.2f}")
        print(f"Range: ₹{cleaned.min_price:.2f} - ₹{cleaned.max_price:.2f}")
        print(f"Average: ₹{cleaned.avg_price:.2f}")
        
        distribution = agent.get_price_distribution(cleaned)
        print(f"\nPrice Distribution:")
        for k, v in distribution.items():
            print(f"  {k}: ₹{v:.2f}")
            
    except ValueError as e:
        print(f"Validation failed: {e}")
