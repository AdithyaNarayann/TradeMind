"""
API Routes - FastAPI Endpoint Definitions

This module defines all HTTP endpoints.
Actual business logic is delegated to the service layer.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any

from schemas.inputs import AnalyticsRequest
from schemas.outputs import AnalyticsResponse
from .service import analytics_service


# Create router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/analytics",
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
    
    **This endpoint is stateless** - all data comes from the request, nothing is persisted.
    
    ## Inputs
    
    - **Product Parameters**: Cost structure (cost_price, selling_price, fees, etc.)
    - **Performance Signals**: Sales activity (chats, orders, units_sold, returns)
    
    ## Outputs
    
    - **Summary Metrics**: Key numbers for dashboard cards
    - **Charts**: Pre-formatted data for Chart.js/Recharts
    - **Insights**: Rule-based business recommendations
    - **Meta**: Flags and warnings for UI decisions
    
    ## Example Use Cases
    
    1. **Dashboard Display**: Fetch all metrics for a seller dashboard
    2. **What-If Simulation**: Change inputs (price, cost) and see projected impact
    3. **Real-time Updates**: Call on slider changes for instant feedback
    """,
    response_description="Complete analytics response with metrics, charts, and insights"
)
async def calculate_analytics(request: AnalyticsRequest) -> AnalyticsResponse:
    """
    Calculate business analytics from request parameters.
    
    This endpoint processes seller inputs and bot signals
    to produce comprehensive business analytics.
    """
    try:
        # Delegate to service layer
        result = analytics_service.calculate(request)
        return result
        
    except ValueError as e:
        # Validation errors from business logic
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation error: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health Check",
    description="Check if the analytics service is operational"
)
async def health_check() -> Dict[str, str]:
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "service": "analytics-engine",
        "version": "1.0.0"
    }


@router.get(
    "/schema",
    summary="Get Input Schema",
    description="Returns the expected input schema for the calculate endpoint"
)
async def get_schema() -> Dict[str, Any]:
    """Return the input schema for documentation purposes."""
    return AnalyticsRequest.model_json_schema()


@router.post(
    "/simulate",
    response_model=AnalyticsResponse,
    summary="Simulate What-If Scenario",
    description="""
    Same as /calculate but semantically indicates this is a simulation.
    
    Use this endpoint when:
    - User is adjusting sliders
    - Running what-if scenarios
    - Comparing different pricing strategies
    
    The calculation logic is identical to /calculate.
    """
)
async def simulate_scenario(request: AnalyticsRequest) -> AnalyticsResponse:
    """
    Simulate a what-if scenario.
    
    Functionally identical to /calculate but indicates simulation intent.
    """
    return await calculate_analytics(request)
