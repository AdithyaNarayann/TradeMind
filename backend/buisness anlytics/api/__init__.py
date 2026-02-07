"""
API Module - FastAPI Routes and Application

Exposes the analytics engine via REST API.
"""

from .routes import router
from .service import AnalyticsService

__all__ = [
    "router",
    "AnalyticsService",
]
