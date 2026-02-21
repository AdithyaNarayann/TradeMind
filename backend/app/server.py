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
    )


if __name__ == "__main__":
    main()
