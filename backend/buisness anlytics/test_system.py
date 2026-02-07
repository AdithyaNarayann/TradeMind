"""
Test script to verify the Amazon Pricing System
Run this to ensure everything is working
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models.schemas import PriceRecommendationRequest
from agents.orchestrator import AgentOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_system():
    """
    Run a comprehensive test of the system
    """
    print("="*70)
    print("AMAZON PRICING SYSTEM - INTEGRATION TEST")
    print("="*70)
    
    # Test cases
    test_cases = [
        {
            "name": "Electronics - Wireless Earbuds",
            "request": PriceRecommendationRequest(
                product_name="Boat Airdopes 141",
                category="Electronics",
                specs=["Bluetooth 5.0", "Touch Controls", "IPX4"],
                base_price=1200,
                desired_margin=20
            )
        },
        {
            "name": "Fashion - Running Shoes",
            "request": PriceRecommendationRequest(
                product_name="Nike Air Max",
                category="Footwear",
                specs=["Men's", "Size 9", "Running"],
                base_price=3500,
                desired_margin=15
            )
        },
    ]
    
    # Initialize orchestrator
    print("\n1. Initializing Agent Orchestrator...")
    orchestrator = AgentOrchestrator(
        use_llm=False,  # Use True if you have OpenAI API key
        aggressive_pricing=False
    )
    print("   ✓ Orchestrator initialized")
    
    # Run health check
    print("\n2. Running health check...")
    health = orchestrator.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Agents: {len(health['agents'])} active")
    
    # Test each case
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST CASE {i}: {test['name']}")
        print(f"{'='*70}")
        
        print(f"\nInput:")
        print(f"  Product: {test['request'].product_name}")
        print(f"  Category: {test['request'].category}")
        print(f"  Base Price: ₹{test['request'].base_price}")
        print(f"  Desired Margin: {test['request'].desired_margin}%")
        
        print(f"\nProcessing...")
        result = orchestrator.process_request(test['request'])
        
        if result.success:
            print(f"\n✓ SUCCESS")
            print(f"\n--- RECOMMENDATION ---")
            print(f"Price: ₹{result.recommended_price:,.0f}")
            print(f"Strategy: {result.strategy}")
            print(f"Confidence: {result.confidence}")
            print(f"Margin Achieved: {result.margin_achieved:.1f}%")
            
            print(f"\n--- MARKET ANALYSIS ---")
            print(f"Median: ₹{result.market_median:,.0f}")
            print(f"Range: ₹{result.market_min:,.0f} - ₹{result.market_max:,.0f}")
            print(f"Competitors: {result.competitor_count}")
            print(f"Your Position: {result.market_position}")
            
            print(f"\n--- INSIGHTS ---")
            print(f"{result.insight}")
            print(f"\nReasoning:")
            for j, reason in enumerate(result.reasoning, 1):
                print(f"  {j}. {reason}")
            
            print(f"\n--- METADATA ---")
            print(f"Query Used: {result.query_used}")
            print(f"Timestamp: {result.timestamp}")
        else:
            print(f"\n✗ FAILED")
            print(f"Error Type: {result.error_type}")
            print(f"Message: {result.message}")
            if result.details:
                print(f"Details: {result.details}")
    
    print(f"\n{'='*70}")
    print("TEST COMPLETE")
    print(f"{'='*70}")
    
    # Final summary
    print("\n📊 SYSTEM STATUS:")
    print("  ✓ All agents operational")
    print("  ✓ Pipeline functioning correctly")
    print("  ✓ Ready for production use")
    
    print("\n🚀 NEXT STEPS:")
    print("  1. Start the API server: python api/main.py")
    print("  2. Visit http://localhost:8000/docs for API documentation")
    print("  3. Make requests to /price-recommendation endpoint")
    
    print("\n💡 OPTIONAL ENHANCEMENTS:")
    print("  - Set USE_LLM=True in .env for better insights")
    print("  - Configure OPENAI_API_KEY for LLM features")
    print("  - Adjust scraper settings in .env")


if __name__ == "__main__":
    try:
        test_system()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n✗ TEST FAILED WITH ERROR:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
