"""
Safety & Rate Control Layer
Protects scraper from getting blocked
"""
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Request throttling and rate limiting
    Keeps your scraper alive
    """
    
    def __init__(
        self,
        max_requests_per_hour: int = 60,
        max_requests_per_day: int = 500,
        min_delay: float = 4.0
    ):
        """
        Args:
            max_requests_per_hour: Maximum requests per hour
            max_requests_per_day: Maximum requests per day
            min_delay: Minimum delay between requests (seconds)
        """
        self.max_requests_per_hour = max_requests_per_hour
        self.max_requests_per_day = max_requests_per_day
        self.min_delay = min_delay
        
        # Track request times
        self.request_times = []
        
        # Last request timestamp
        self.last_request_time: Optional[float] = None
    
    def wait_if_needed(self):
        """
        Wait if necessary to respect rate limits
        Call this BEFORE making a request
        """
        now = time.time()
        
        # Enforce minimum delay
        if self.last_request_time is not None:
            time_since_last = now - self.last_request_time
            
            if time_since_last < self.min_delay:
                sleep_time = self.min_delay - time_since_last
                logger.debug(f"Rate limit: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                now = time.time()
        
        # Clean old timestamps (older than 24 hours)
        cutoff = now - 86400  # 24 hours in seconds
        self.request_times = [t for t in self.request_times if t > cutoff]
        
        # Check hourly limit
        hour_ago = now - 3600
        recent_requests = sum(1 for t in self.request_times if t > hour_ago)
        
        if recent_requests >= self.max_requests_per_hour:
            # Wait until the oldest request in the hour expires
            oldest_in_hour = min(t for t in self.request_times if t > hour_ago)
            wait_time = (oldest_in_hour + 3600) - now
            
            logger.warning(
                f"Hourly rate limit reached ({recent_requests}/{self.max_requests_per_hour}). "
                f"Waiting {wait_time:.0f}s"
            )
            time.sleep(wait_time + 1)
            now = time.time()
        
        # Check daily limit
        if len(self.request_times) >= self.max_requests_per_day:
            logger.error(
                f"Daily rate limit reached ({len(self.request_times)}/{self.max_requests_per_day})"
            )
            raise RateLimitExceeded(
                f"Daily limit of {self.max_requests_per_day} requests exceeded. "
                "Try again tomorrow."
            )
        
        # Record this request
        self.request_times.append(now)
        self.last_request_time = now
    
    def get_stats(self) -> dict:
        """Get current rate limit stats"""
        now = time.time()
        hour_ago = now - 3600
        
        return {
            "requests_last_hour": sum(1 for t in self.request_times if t > hour_ago),
            "max_per_hour": self.max_requests_per_hour,
            "requests_today": len(self.request_times),
            "max_per_day": self.max_requests_per_day,
            "min_delay": self.min_delay
        }


class RetryHandler:
    """
    Smart retry logic with exponential backoff
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 60.0
    ):
        """
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial retry delay (seconds)
            max_delay: Maximum retry delay (seconds)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def execute_with_retry(self, func, *args, **kwargs):
        """
        Execute function with retry logic
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    # Calculate backoff delay
                    delay = min(
                        self.base_delay * (2 ** attempt),
                        self.max_delay
                    )
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} retry attempts failed"
                    )
        
        # All retries exhausted
        raise last_exception


class RequestTracker:
    """
    Track and monitor scraping activity
    """
    
    def __init__(self):
        self.stats = defaultdict(int)
        self.errors = defaultdict(int)
        self.start_time = datetime.now()
    
    def record_request(self, success: bool, error_type: Optional[str] = None):
        """Record a request attempt"""
        self.stats['total_requests'] += 1
        
        if success:
            self.stats['successful_requests'] += 1
        else:
            self.stats['failed_requests'] += 1
            if error_type:
                self.errors[error_type] += 1
    
    def record_products_scraped(self, count: int):
        """Record number of products scraped"""
        self.stats['total_products'] += count
    
    def get_report(self) -> dict:
        """Get activity report"""
        uptime = datetime.now() - self.start_time
        
        success_rate = 0
        if self.stats['total_requests'] > 0:
            success_rate = (
                self.stats['successful_requests'] / self.stats['total_requests']
            ) * 100
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "total_requests": self.stats['total_requests'],
            "successful_requests": self.stats['successful_requests'],
            "failed_requests": self.stats['failed_requests'],
            "success_rate": f"{success_rate:.1f}%",
            "total_products_scraped": self.stats['total_products'],
            "errors": dict(self.errors)
        }


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass


# ===== USAGE EXAMPLE =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test rate limiter
    rate_limiter = RateLimiter(
        max_requests_per_hour=10,
        max_requests_per_day=50,
        min_delay=2.0
    )
    
    print("Testing rate limiter...")
    for i in range(5):
        print(f"\nRequest {i+1}")
        rate_limiter.wait_if_needed()
        print("Request allowed")
        
        stats = rate_limiter.get_stats()
        print(f"Stats: {stats}")
    
    # Test retry handler
    print("\n\nTesting retry handler...")
    retry_handler = RetryHandler(max_retries=3, base_delay=1.0)
    
    def flaky_function(attempt=[0]):
        """Function that fails first 2 times"""
        attempt[0] += 1
        if attempt[0] < 3:
            raise ValueError(f"Attempt {attempt[0]} failed")
        return "Success!"
    
    try:
        result = retry_handler.execute_with_retry(flaky_function)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed: {e}")
