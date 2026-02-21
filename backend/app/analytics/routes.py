"""
Analytics API Routes

Endpoints for the business analytics engine.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from .schemas import AnalyticsRequest, AnalyticsResponse
from .service import analytics_service


router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["Analytics"],
    responses={
        400: {"description": "Invalid input parameters"},
        500: {"description": "Internal calculation error"},
    }
)


@router.post(
    "/calculate",
    response_model=AnalyticsResponse,
    summary="Calculate Business Analytics",
    description="""
    Calculate comprehensive business analytics from product parameters and performance signals.
    
    **This endpoint is stateless** - all data comes from the request.
    
    ## Outputs
    - **Summary Metrics**: Key numbers for dashboard cards
    - **Charts**: Pre-formatted data for Chart.js/Recharts
    - **Insights**: Rule-based business recommendations
    - **Meta**: Flags and warnings
    """
)
async def calculate_analytics(request: AnalyticsRequest) -> AnalyticsResponse:
    """Calculate business analytics from request parameters."""
    try:
        return analytics_service.calculate(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Calculation error: {str(e)}")


@router.get(
    "/health",
    summary="Analytics Health Check"
)
async def analytics_health() -> Dict[str, str]:
    """Health check for analytics service."""
    return {"status": "healthy", "service": "analytics-engine"}


@router.get(
    "/schema",
    summary="Get Input Schema"
)
async def get_schema() -> Dict[str, Any]:
    """Return the input schema."""
    return AnalyticsRequest.model_json_schema()


@router.post(
    "/simulate",
    response_model=AnalyticsResponse,
    summary="Simulate What-If Scenario",
    description="Same as /calculate but semantically indicates simulation intent."
)
async def simulate_scenario(request: AnalyticsRequest) -> AnalyticsResponse:
    """Simulate a what-if scenario."""
    return await calculate_analytics(request)
