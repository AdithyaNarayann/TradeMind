"""
Negotiation Engine Backend

A profit-aware negotiation engine for commercial use.
"""
from .app import app, create_app
from .core import NegotiationEngine, get_engine
from .models import (
    NegotiationMode,
    CreateSessionRequest,
    CreateSessionResponse,
    BuyerOffer,
    NegotiationTurnResponse,
)

__version__ = "1.0.0"

__all__ = [
    "app",
    "create_app",
    "NegotiationEngine",
    "get_engine",
    "NegotiationMode",
    "CreateSessionRequest",
    "CreateSessionResponse",
    "BuyerOffer",
    "NegotiationTurnResponse",
]
