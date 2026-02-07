"""
Storage Layer - SQLite caching to avoid re-scraping
MVP-safe, simple, effective
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class CacheStorage:
    """
    Simple SQLite-based cache for scraped data
    
    Purpose:
    - Avoid re-scraping same queries
    - Speed up repeated requests
    - Reduce load on Amazon
    """
    
    # Cache validity period
    CACHE_HOURS = 24  # Results valid for 24 hours
    
    def __init__(self, db_path: str = "data/cache.db"):
        """
        Initialize cache database
        
        Args:
            db_path: Path to SQLite database file
        """
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table for cached scrape results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrape_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_query TEXT NOT NULL,
                    scraped_at TIMESTAMP NOT NULL,
                    product_count INTEGER NOT NULL,
                    market_median REAL NOT NULL,
                    market_min REAL NOT NULL,
                    market_max REAL NOT NULL,
                    market_avg REAL NOT NULL,
                    clean_prices TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_query 
                ON scrape_cache(search_query, scraped_at)
            """)
            
            conn.commit()
            
        logger.info(f"Cache storage initialized at {self.db_path}")
    
    def get_cached_result(self, search_query: str) -> Optional[dict]:
        """
        Get cached result if available and fresh
        
        Args:
            search_query: The search query to look up
            
        Returns:
            Cached data dict or None if not found/expired
        """
        cutoff_time = datetime.now() - timedelta(hours=self.CACHE_HOURS)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    product_count,
                    market_median,
                    market_min,
                    market_max,
                    market_avg,
                    clean_prices,
                    scraped_at
                FROM scrape_cache
                WHERE search_query = ?
                  AND scraped_at > ?
                ORDER BY scraped_at DESC
                LIMIT 1
            """, (search_query, cutoff_time))
            
            row = cursor.fetchone()
            
            if row:
                logger.info(f"Cache HIT for query: '{search_query}'")
                
                return {
                    "product_count": row[0],
                    "market_median": row[1],
                    "market_min": row[2],
                    "market_max": row[3],
                    "market_avg": row[4],
                    "clean_prices": json.loads(row[5]),
                    "scraped_at": row[6]
                }
            else:
                logger.info(f"Cache MISS for query: '{search_query}'")
                return None
    
    def store_result(
        self,
        search_query: str,
        clean_prices: List[float],
        market_median: float,
        market_min: float,
        market_max: float,
        market_avg: float
    ):
        """
        Store scrape result in cache
        
        Args:
            search_query: The search query used
            clean_prices: List of cleaned prices
            market_median: Median price
            market_min: Minimum price
            market_max: Maximum price
            market_avg: Average price
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO scrape_cache (
                    search_query,
                    scraped_at,
                    product_count,
                    market_median,
                    market_min,
                    market_max,
                    market_avg,
                    clean_prices
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                search_query,
                datetime.now(),
                len(clean_prices),
                market_median,
                market_min,
                market_max,
                market_avg,
                json.dumps(clean_prices)
            ))
            
            conn.commit()
            
        logger.info(f"Cached result for query: '{search_query}'")
    
    def clear_old_cache(self, days: int = 7):
        """
        Clear cache entries older than specified days
        
        Args:
            days: Remove entries older than this many days
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM scrape_cache
                WHERE scraped_at < ?
            """, (cutoff_time,))
            
            deleted = cursor.rowcount
            conn.commit()
            
        logger.info(f"Cleared {deleted} old cache entries")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total entries
            cursor.execute("SELECT COUNT(*) FROM scrape_cache")
            total = cursor.fetchone()[0]
            
            # Fresh entries (within cache period)
            cutoff_time = datetime.now() - timedelta(hours=self.CACHE_HOURS)
            cursor.execute("""
                SELECT COUNT(*) FROM scrape_cache
                WHERE scraped_at > ?
            """, (cutoff_time,))
            fresh = cursor.fetchone()[0]
            
            # Oldest entry
            cursor.execute("""
                SELECT MIN(scraped_at) FROM scrape_cache
            """)
            oldest = cursor.fetchone()[0]
            
            # Newest entry
            cursor.execute("""
                SELECT MAX(scraped_at) FROM scrape_cache
            """)
            newest = cursor.fetchone()[0]
            
        return {
            "total_entries": total,
            "fresh_entries": fresh,
            "oldest_entry": oldest,
            "newest_entry": newest,
            "cache_hours": self.CACHE_HOURS
        }


# ===== USAGE EXAMPLE =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize cache
    cache = CacheStorage(db_path="test_cache.db")
    
    # Test store
    cache.store_result(
        search_query="boat wireless earbuds bluetooth",
        clean_prices=[1899.0, 1949.0, 1999.0, 2049.0, 2099.0],
        market_median=1999.0,
        market_min=1899.0,
        market_max=2099.0,
        market_avg=2019.0
    )
    
    # Test retrieve
    result = cache.get_cached_result("boat wireless earbuds bluetooth")
    
    if result:
        print("Cached result found:")
        print(f"  Median: ₹{result['market_median']}")
        print(f"  Products: {result['product_count']}")
        print(f"  Scraped: {result['scraped_at']}")
    
    # Get stats
    stats = cache.get_stats()
    print("\nCache stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
