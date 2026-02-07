"""
FastAPI Application - API Layer
Entry point for the pricing system
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Optional

from models.schemas import (
    PriceRecommendationRequest,
    PriceRecommendationResponse,
    ErrorResponse
)
from agents.orchestrator import AgentOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: Optional[AgentOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    """
    global orchestrator
    
    # Startup
    logger.info("Starting Amazon Pricing System API...")
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator(
        use_llm=False,  # Set to True and provide API key for LLM features
        aggressive_pricing=False
    )
    
    logger.info("Orchestrator initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")


# Create FastAPI app
app = FastAPI(
    title="Amazon Pricing System",
    description="Autonomous AI agents for intelligent Amazon product pricing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== ENDPOINTS =====

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Amazon Pricing System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    if orchestrator is None:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": "Orchestrator not initialized"}
        )
    
    health = orchestrator.health_check()
    return health


@app.post(
    "/price-recommendation",
    response_model=PriceRecommendationResponse,
    responses={
        200: {"description": "Successful pricing recommendation"},
        400: {"description": "Invalid request"},
        500: {"description": "Server error"}
    }
)
async def get_price_recommendation(
    request: PriceRecommendationRequest
) -> PriceRecommendationResponse | ErrorResponse:
    """
    Get AI-powered pricing recommendation
    
    **Process:**
    1. Analyzes Amazon market data for similar products
    2. Applies intelligent pricing strategy
    3. Returns explainable recommendation with insights
    
    **Example Request:**
    ```json
    {
      "product_name": "Boat wireless earbuds",
      "category": "Electronics",
      "specs": ["Bluetooth 5.3", "Noise Cancellation"],
      "base_price": 1200,
      "desired_margin": 20
    }
    ```
    """
    try:
        if orchestrator is None:
            raise HTTPException(
                status_code=503,
                detail="Service unavailable: Orchestrator not initialized"
            )
        
        logger.info(f"Received pricing request for: {request.product_name}")
        
        # Validate input
        if request.base_price <= 0:
            raise HTTPException(
                status_code=400,
                detail="base_price must be greater than 0"
            )
        
        if not (0 <= request.desired_margin <= 100):
            raise HTTPException(
                status_code=400,
                detail="desired_margin must be between 0 and 100"
            )
        
        # Process request through orchestrator
        result = orchestrator.process_request(request)
        
        # If error occurred in processing
        if not result.success:
            # Return error with 200 status (business logic error, not HTTP error)
            return result
        
        logger.info(
            f"Successfully processed request: ₹{result.recommended_price} "
            f"({result.strategy})"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/config")
async def get_config():
    """
    Get current system configuration
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    return {
        "llm_enabled": orchestrator.use_llm,
        "aggressive_pricing": orchestrator.pricing_agent.aggressive_mode,
        "min_products_threshold": orchestrator.MIN_PRODUCTS_THRESHOLD,
        "scraper": {
            "target_products": orchestrator.scraper.TARGET_PRODUCTS,
            "max_pages": orchestrator.scraper.MAX_PAGES,
            "delay_range": f"{orchestrator.scraper.MIN_DELAY}-{orchestrator.scraper.MAX_DELAY}s"
        }
    }


# ===== ERROR HANDLERS =====

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors"""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error_type": "validation_error",
            "message": str(exc)
        }
    )


# ===== RUN SERVER =====
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable for development
        log_level="info"
    )
