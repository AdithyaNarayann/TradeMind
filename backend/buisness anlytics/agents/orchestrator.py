"""
AGENT ORCHESTRATOR - The Brain 🧠
Purpose: Control agent execution, handle failures, decide when to stop
"""
import logging
from datetime import datetime
from typing import Optional

from models.schemas import (
    PriceRecommendationRequest,
    PriceRecommendationResponse,
    ErrorResponse
)
from agents.query_builder import QueryBuilderAgent
from agents.amazon_scraper import AmazonScraperAgent
from agents.data_cleaning import DataCleaningAgent
from agents.pricing_strategy import PricingStrategyAgent
from agents.insight_generator import InsightGeneratorAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates the entire agentic pipeline
    
    Pipeline:
    1. Query Builder → optimized search query
    2. Amazon Scraper → raw market data
    3. Data Cleaning → validated dataset
    4. Pricing Strategy → pricing decision
    5. Insight Generator → explainable output
    """
    
    # Quality thresholds
    MIN_PRODUCTS_THRESHOLD = 5  # Abort if fewer products
    
    def __init__(
        self,
        use_llm: bool = False,
        llm_client = None,
        aggressive_pricing: bool = False
    ):
        """
        Initialize all agents
        
        Args:
            use_llm: Enable LLM for Query Builder and Insight Generator
            llm_client: OpenAI client (if use_llm=True)
            aggressive_pricing: Use aggressive pricing strategy
        """
        self.use_llm = use_llm
        self.llm_client = llm_client
        
        # Initialize agents
        self.query_builder = QueryBuilderAgent(
            use_llm=use_llm,
            llm_client=llm_client
        )
        
        self.scraper = AmazonScraperAgent()
        
        self.data_cleaner = DataCleaningAgent()
        
        self.pricing_agent = PricingStrategyAgent(
            aggressive_mode=aggressive_pricing
        )
        
        self.insight_generator = InsightGeneratorAgent(
            llm_client=llm_client,
            use_llm=use_llm
        )
        
        logger.info(
            f"Orchestrator initialized (LLM: {use_llm}, "
            f"Aggressive: {aggressive_pricing})"
        )
    
    def process_request(
        self,
        request: PriceRecommendationRequest
    ) -> PriceRecommendationResponse | ErrorResponse:
        """
        Execute the full agentic pipeline
        
        Args:
            request: Seller's pricing request
            
        Returns:
            PriceRecommendationResponse or ErrorResponse
        """
        logger.info(
            f"Processing request: {request.product_name} "
            f"(base: ₹{request.base_price}, margin: {request.desired_margin}%)"
        )
        
        try:
            # STEP 1: Build optimized query
            logger.info("STEP 1: Building search query...")
            search_query = self.query_builder.build_query(
                product_name=request.product_name,
                category=request.category,
                specs=request.specs
            )
            
            # Validate query
            if not self.query_builder.validate_query(search_query):
                return self._error_response(
                    "query_invalid",
                    "Could not build valid search query from product details"
                )
            
            logger.info(f"Query built: '{search_query}'")
            
            # STEP 2: Scrape Amazon
            logger.info("STEP 2: Scraping Amazon...")
            raw_products = self.scraper.scrape_search_results(search_query)
            
            # Check if we got enough data
            if len(raw_products) < self.MIN_PRODUCTS_THRESHOLD:
                return self._error_response(
                    "insufficient_data",
                    f"Only found {len(raw_products)} products. "
                    f"Need at least {self.MIN_PRODUCTS_THRESHOLD} for reliable pricing.",
                    details={"products_found": len(raw_products)}
                )
            
            logger.info(f"Scraped {len(raw_products)} products")
            
            # STEP 3: Clean and validate data
            logger.info("STEP 3: Cleaning data...")
            try:
                market_data = self.data_cleaner.clean_and_validate(
                    raw_products,
                    reference_price=request.base_price
                )
            except ValueError as e:
                return self._error_response(
                    "data_quality_poor",
                    str(e)
                )
            
            logger.info(
                f"Data cleaned: {market_data.product_count} products, "
                f"median ₹{market_data.median_price:.2f}"
            )
            
            # STEP 4: Compute pricing strategy
            logger.info("STEP 4: Computing pricing strategy...")
            pricing_decision = self.pricing_agent.compute_pricing_decision(
                market_data=market_data,
                base_price=request.base_price,
                desired_margin=request.desired_margin
            )
            
            # Validate recommendation
            is_valid, warning = self.pricing_agent.validate_recommendation(
                pricing_decision,
                request.base_price
            )
            
            if not is_valid:
                return self._error_response(
                    "pricing_invalid",
                    warning
                )
            
            logger.info(
                f"Pricing decision: ₹{pricing_decision.recommended_price:.2f} "
                f"({pricing_decision.strategy})"
            )
            
            # STEP 5: Generate insights
            logger.info("STEP 5: Generating insights...")
            insight, reasoning = self.insight_generator.generate_insights(
                decision=pricing_decision,
                market_data=market_data,
                base_price=request.base_price,
                desired_margin=request.desired_margin
            )
            
            # Build final response
            response = PriceRecommendationResponse(
                success=True,
                recommended_price=pricing_decision.recommended_price,
                strategy=pricing_decision.strategy,
                confidence=pricing_decision.confidence,
                market_median=market_data.median_price,
                market_min=market_data.min_price,
                market_max=market_data.max_price,
                competitor_count=market_data.product_count,
                margin_achieved=pricing_decision.margin_achieved,
                market_position=pricing_decision.market_position,
                insight=insight,
                reasoning=reasoning,
                timestamp=datetime.now().isoformat(),
                query_used=search_query
            )
            
            logger.info("Pipeline completed successfully")
            return response
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return self._error_response(
                "pipeline_error",
                f"An unexpected error occurred: {str(e)}"
            )
    
    def _error_response(
        self,
        error_type: str,
        message: str,
        details: Optional[dict] = None
    ) -> ErrorResponse:
        """Create standardized error response"""
        logger.error(f"{error_type}: {message}")
        
        return ErrorResponse(
            success=False,
            error_type=error_type,
            message=message,
            details=details
        )
    
    def health_check(self) -> dict:
        """
        Check if all agents are functioning
        
        Returns:
            Health status dictionary
        """
        health = {
            "status": "healthy",
            "agents": {
                "query_builder": "ok",
                "scraper": "ok",
                "data_cleaner": "ok",
                "pricing_agent": "ok",
                "insight_generator": "ok"
            },
            "llm_enabled": self.use_llm
        }
        
        # Could add actual agent health checks here
        
        return health


# ===== USAGE EXAMPLE =====
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize orchestrator (without LLM for testing)
    orchestrator = AgentOrchestrator(
        use_llm=False,
        aggressive_pricing=False
    )
    
    # Test request
    test_request = PriceRecommendationRequest(
        product_name="Boat Airdopes 141",
        category="Electronics",
        specs=["Bluetooth 5.0", "Touch Controls", "IPX4"],
        base_price=1200,
        desired_margin=20
    )
    
    print("="*70)
    print("STARTING PRICING PIPELINE")
    print("="*70)
    
    # Process
    result = orchestrator.process_request(test_request)
    
    print("\n" + "="*70)
    print("RESULT")
    print("="*70)
    
    if result.success:
        print(f"\n✓ SUCCESS")
        print(f"\nRecommended Price: ₹{result.recommended_price:,.0f}")
        print(f"Strategy: {result.strategy}")
        print(f"Confidence: {result.confidence}")
        print(f"Margin: {result.margin_achieved:.1f}%")
        print(f"\nMarket Context:")
        print(f"  Median: ₹{result.market_median:,.0f}")
        print(f"  Range: ₹{result.market_min:,.0f} - ₹{result.market_max:,.0f}")
        print(f"  Competitors: {result.competitor_count}")
        print(f"\nInsight:")
        print(f"  {result.insight}")
        print(f"\nReasoning:")
        for i, point in enumerate(result.reasoning, 1):
            print(f"  {i}. {point}")
    else:
        print(f"\n✗ FAILED")
        print(f"Error: {result.error_type}")
        print(f"Message: {result.message}")
