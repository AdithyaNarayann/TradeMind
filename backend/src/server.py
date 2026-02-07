"""
Negotiation Engine - Server Entry Point

Run with: python -m src.server
Or with uvicorn: uvicorn src.app:app --reload
"""
import uvicorn
from .config import get_settings


def main():
    """Start the server."""
    settings = get_settings()
    
    uvicorn.run(
        "src.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
