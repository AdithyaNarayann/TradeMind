"""
Rate Limiting Middleware

Implements tiered rate limiting:
- Per-minute limits for burst protection
- Per-hour limits for sustained protection
- Custom limits per endpoint
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse
from typing import Callable

from ...core.config import get_settings


settings = get_settings()


def custom_key_func(request: Request) -> str:
    """
    Custom key function for rate limiting.
    
    SECURITY: Only trust proxy headers when behind a known reverse proxy.
    In production, configure TRUSTED_PROXY_IPS or use uvicorn --proxy-headers
    with --forwarded-allow-ips to prevent IP spoofing.
    
    Falls back to the direct client IP for safety.
    """
    # Only trust proxy headers in production behind a known proxy
    # For now, always use the direct connection IP to prevent spoofing
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=custom_key_func,
    default_limits=[
        f"{settings.rate_limit_per_minute}/minute",
        f"{settings.rate_limit_per_hour}/hour",
    ],
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60),
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
            "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
        },
    )


# Custom rate limit decorators for different endpoints
def strict_limit(func: Callable) -> Callable:
    """Apply strict rate limit for sensitive endpoints."""
    return limiter.limit("10/minute")(func)


def standard_limit(func: Callable) -> Callable:
    """Apply standard rate limit."""
    return limiter.limit(f"{settings.rate_limit_per_minute}/minute")(func)


def relaxed_limit(func: Callable) -> Callable:
    """Apply relaxed rate limit for read-only endpoints."""
    return limiter.limit("120/minute")(func)
