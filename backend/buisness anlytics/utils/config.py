"""
Configuration management
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings
    Load from environment variables or .env file
    """
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # LLM Settings (Optional)
    use_llm: bool = False
    openai_api_key: Optional[str] = None
    llm_model: str = "gpt-3.5-turbo"
    
    # Pricing Strategy
    aggressive_pricing: bool = False
    min_margin_threshold: float = 5.0
    warning_margin_threshold: float = 10.0
    
    # Scraper Settings
    scraper_target_products: int = 25
    scraper_max_pages: int = 2
    scraper_min_delay: int = 4
    scraper_max_delay: int = 8
    min_reviews_threshold: int = 10
    
    # Data Quality
    min_products_for_analysis: int = 5
    iqr_multiplier: float = 2.5
    
    # Cache Settings
    cache_enabled: bool = True
    cache_hours: int = 24
    cache_db_path: str = "data/cache.db"
    
    # Rate Limiting
    max_requests_per_hour: int = 60
    max_requests_per_day: int = 500
    
    # Retry Settings
    max_retries: int = 3
    retry_base_delay: float = 2.0
    retry_max_delay: float = 60.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
