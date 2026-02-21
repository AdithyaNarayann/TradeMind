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
    
    Uses:
    1. X-Forwarded-For header (for proxied requests)
    2. X-Real-IP header
    3. Client IP from request
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
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
