"""
Negotiation Engine - FastAPI Application

This is the main application factory that creates and configures
the FastAPI application with all routes, middleware, and error handlers.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import structlog

from .config import get_settings
from .api import (
    router,
    limiter,
    rate_limit_exceeded_handler,
    ErrorHandlerMiddleware,
    validation_exception_handler,
    http_exception_handler,
    value_error_handler,
)
from .analytics import analytics_router

# Import competitive intelligence router from buisness anlytics module
import sys, os
_ba_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "buisness anlytics")
if _ba_path not in sys.path:
    sys.path.insert(0, _ba_path)
from competitive_intelligence import competitive_router


settings = get_settings()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(
        "starting_application",
        env=settings.env,
        debug=settings.debug,
    )
    yield
    logger.info("shutting_down_application")


def create_app() -> FastAPI:
    """
    Application factory.
    
    Creates and configures the FastAPI application.
    """
    app = FastAPI(
        title="Negotiation Engine API",
        description="""
        A profit-aware negotiation engine for commercial use.
        
        ## Features
        
        - **MAX_PROFIT Mode**: Maximize seller profit with conservative concessions
        - **MIN_LOSS Mode**: Minimize loss when profit isn't achievable
        - **Deterministic Pricing**: Rule-based, auditable pricing decisions
        - **Constraint Enforcement**: Never violates seller-defined limits
        
        ## Architecture
        
        The engine uses a multi-agent architecture:
        1. **Context Analysis Agent**: Computes strategic posture
        2. **Pricing Strategy Agent**: Makes all numeric decisions (no LLM)
        3. **Conversation Agent**: Generates natural language responses
        
        ## Usage Flow
        
        1. Create session with product/inventory/strategy data
        2. Present initial offer to buyer
        3. Submit buyer's counter-offers
        4. Engine responds with accept/counter/reject
        5. Session closes when deal is made or constraints are violated
        """,
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # Add rate limiter to app state
    app.state.limiter = limiter
    
    # ==========================================================================
    # Middleware (order matters - last added = first executed)
    # ==========================================================================
    
    # Error handler middleware
    app.add_middleware(ErrorHandlerMiddleware)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ==========================================================================
    # Exception Handlers
    # ==========================================================================
    
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    
    # ==========================================================================
    # Routes
    # ==========================================================================
    
    app.include_router(router)
    app.include_router(analytics_router)
    app.include_router(competitive_router)
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API info."""
        return {
            "name": "Negotiation Engine API",
            "version": "1.0.0",
            "docs": "/docs" if settings.debug else None,
            "health": "/api/v1/negotiate/health",
            "analytics": "/api/v1/analytics/calculate",
        }
    
    return app


# Create default app instance
app = create_app()
