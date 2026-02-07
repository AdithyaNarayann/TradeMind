"""
Business Analytics Engine - Main Application Entry Point

A stateless analytics API for e-commerce seller dashboards.
Built with FastAPI for high performance and automatic documentation.

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8001

Or:
    python main.py
"""

import sys
from pathlib import Path

# Add the buisness anlytics directory to Python path
# This allows imports like `from schemas import ...` to work
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from api import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    logger.info("Starting Business Analytics Engine...")
    yield
    logger.info("Shutting down Business Analytics Engine...")


# Create FastAPI application
app = FastAPI(
    title="Business Analytics Engine",
    description="""
    ## Stateless Analytics API for E-commerce Sellers
    
    This API calculates business metrics, generates chart-ready data,
    and provides rule-based insights - all from request parameters.
    
    ### Features
    
    - **No Database**: Everything computed from inputs
    - **Chart-Ready Output**: Direct consumption by Chart.js, Recharts, etc.
    - **Rule-Based Insights**: Actionable recommendations
    - **Simulation-Ready**: What-if scenario support
    
    ### Use Cases
    
    - Real-time dashboard updates
    - What-if price simulations
    - Performance monitoring
    - AI agent integration
    
    ### Architecture
    
    ```
    Request → Validation → Calculations → Charts → Insights → Response
    ```
    
    All computation is stateless and deterministic.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
# In production, replace "*" with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include analytics routes
app.include_router(router)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Business Analytics Engine",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "calculate": "POST /analytics/calculate",
            "simulate": "POST /analytics/simulate",
            "health": "GET /analytics/health",
            "schema": "GET /analytics/schema"
        }
    }


# Run with uvicorn if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,  # Different port from main backend (8000)
        reload=True,
        log_level="info"
    )
