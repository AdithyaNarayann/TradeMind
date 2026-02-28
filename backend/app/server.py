"""
Negotiation Engine - Server Entry Point

Run with: python -m app.server
Or with uvicorn: uvicorn app.main:app --reload
"""
import uvicorn
from .core.config import get_settings


def main():
    """Start the server."""
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        # SECURITY: Limit request body size to 10 MB to prevent DoS
        limit_max_request_line=8190,
        # SECURITY: Limit concurrent connections
        limit_concurrency=100,
        # SECURITY: Set header size limits
        h11_max_incomplete_event_size=16384,
    )


if __name__ == "__main__":
    main()
