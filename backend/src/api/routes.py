"""
Negotiation API Routes

Main API endpoints for the negotiation engine.
All endpoints are designed to be:
- RESTful
- Rate-limited
- Fully documented
- Production-ready
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from uuid import UUID
from typing import Optional

from ..models import (
    CreateSessionRequest,
    CreateSessionResponse,
    BuyerOffer,
    NegotiationTurnResponse,
    SessionSummary,
    NegotiationAnalytics,
)
from ..core import get_engine, NegotiationEngine
from .middleware import limiter


router = APIRouter(prefix="/api/v1/negotiate", tags=["Negotiation"])


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


# =============================================================================
# Session Management Endpoints
# =============================================================================

@router.post(
    "/sessions",
    response_model=CreateSessionResponse,
    summary="Create Negotiation Session",
    description="""
    Create a new negotiation session with seller-defined parameters.
    
    This endpoint initializes a negotiation with:
    - Product and cost data
    - Inventory context
    - Strategic controls (mode, urgency, etc.)
    
    Returns the session ID and initial offer to present to buyer.
    """,
)
@limiter.limit("20/minute")
async def create_session(
    request: Request,
    body: CreateSessionRequest,
    engine: NegotiationEngine = Depends(get_engine),
) -> CreateSessionResponse:
    """Create a new negotiation session."""
    client_ip = get_client_ip(request)
    
    response = engine.create_session(
        request=body,
        client_ip=client_ip,
    )
    
    return response


@router.get(
    "/sessions/{session_id}",
    response_model=SessionSummary,
    summary="Get Session Status",
    description="Retrieve the current status and summary of a negotiation session.",
)
@limiter.limit("60/minute")
async def get_session(
    request: Request,
    session_id: UUID,
    engine: NegotiationEngine = Depends(get_engine),
) -> SessionSummary:
    """Get session summary by ID."""
    summary = engine.get_session(session_id)
    
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found or expired",
        )
    
    return summary


@router.delete(
    "/sessions/{session_id}",
    response_model=SessionSummary,
    summary="End Session",
    description="End a negotiation session early (buyer walked away or manual termination).",
)
@limiter.limit("30/minute")
async def end_session(
    request: Request,
    session_id: UUID,
    reason: Optional[str] = "buyer_walked",
    engine: NegotiationEngine = Depends(get_engine),
) -> SessionSummary:
    """End a negotiation session."""
    try:
        summary = engine.end_session(session_id, reason)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Negotiation Turn Endpoints
# =============================================================================

@router.post(
    "/sessions/{session_id}/turns",
    response_model=NegotiationTurnResponse,
    summary="Submit Buyer Offer",
    description="""
    Submit a buyer's offer and receive the seller's response.
    
    The engine will:
    1. Validate the offer against constraints
    2. Compute the pricing decision (accept/counter/reject)
    3. Generate a natural language response
    4. Update session state
    
    Returns full pricing decision, message, and session state.
    """,
)
@limiter.limit("30/minute")
async def submit_offer(
    request: Request,
    session_id: UUID,
    body: BuyerOffer,
    engine: NegotiationEngine = Depends(get_engine),
) -> NegotiationTurnResponse:
    """Process a negotiation turn with buyer's offer."""
    try:
        response = engine.process_turn(
            session_id=session_id,
            buyer_offer=body,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Analytics Endpoints
# =============================================================================

@router.get(
    "/sessions/{session_id}/analytics",
    response_model=NegotiationAnalytics,
    summary="Get Session Analytics",
    description="""
    Get detailed analytics for a negotiation session.
    
    Includes:
    - Price journey (start to finish)
    - Concession analysis
    - Efficiency metrics
    - Profit calculations
    """,
)
@limiter.limit("30/minute")
async def get_analytics(
    request: Request,
    session_id: UUID,
    engine: NegotiationEngine = Depends(get_engine),
) -> NegotiationAnalytics:
    """Get detailed analytics for a session."""
    analytics = engine.get_analytics(session_id)
    
    if analytics is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )
    
    return analytics


# =============================================================================
# Health & Status Endpoints
# =============================================================================

@router.get(
    "/health",
    summary="Health Check",
    description="Check API health and basic stats.",
)
@limiter.limit("120/minute")
async def health_check(request: Request):
    """Simple health check endpoint."""
    from ..core import get_session_manager
    
    session_manager = get_session_manager()
    
    return {
        "status": "healthy",
        "active_sessions": session_manager.get_active_count(),
    }
