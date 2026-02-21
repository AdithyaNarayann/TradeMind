"""
Negotiation Engine Backend - Configuration Module
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    # Session Management
    session_ttl_seconds: int = 3600  # 1 hour
    max_sessions_per_client: int = 10
    
    # OpenRouter LLM
    openrouter_api_key: str = ""  # Get from https://openrouter.ai/keys
    openrouter_model: str = "google/gemini-2.0-flash-001"  # Fast & cheap
    llm_max_tokens: int = 200
    llm_temperature: float = 0.7
    llm_timeout_seconds: float = 10.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
