"""
AGENT 4: Pricing Strategy Agent
Purpose: Core pricing intelligence - where monetization lives
Type: Business logic agent (proprietary IP)
"""
import logging
from typing import Tuple

from models.schemas import CleanedMarketData, PricingDecision

logger = logging.getLogger(__name__)


class PricingStrategyAgent:
    """
    Makes intelligent pricing decisions based on market data
    This is the core IP of the system
    """
    
    # Strategy thresholds (configurable per business model)
    COMPETITIVE_THRESHOLD = 0.95  # Price at 95% of median = competitive
    NEUTRAL_THRESHOLD = 1.05      # Price at 105% of median = neutral
    
    # Margin thresholds
    MIN_ACCEPTABLE_MARGIN = 5.0   # Minimum margin %
    WARNING_MARGIN = 10.0         # Warn if below this
    
    def __init__(self, aggressive_mode: bool = False):
        """
        Args:
            aggressive_mode: If True, recommends more competitive pricing
        """
        self.aggressive_mode = aggressive_mode
    
    def compute_pricing_decision(
        self,
        market_data: CleanedMarketData,
        base_price: float,
        desired_margin: float
    ) -> PricingDecision:
        """
        Compute optimal pricing strategy
        
        Args:
            market_data: Cleaned market statistics
            base_price: Seller's cost/base price
            desired_margin: Seller's target margin %
            
        Returns:
            PricingDecision with recommendation and reasoning
        """
        logger.info(
            f"Computing pricing: base=₹{base_price:.2f}, "
            f"desired_margin={desired_margin}%, market_median=₹{market_data.median_price:.2f}"
        )
        
        # Step 1: Calculate minimum viable price
        min_viable_price = self._calculate_min_price(base_price, self.MIN_ACCEPTABLE_MARGIN)
        
        # Step 2: Calculate target price with desired margin
        target_price = self._calculate_target_price(base_price, desired_margin)
        
        # Step 3: Analyze market position
        market_position = self._analyze_market_position(
            target_price,
            market_data.median_price,
            market_data.min_price,
            market_data.max_price
        )
        
        # Step 4: Choose strategy
        recommended_price, strategy, confidence = self._choose_strategy(
            base_price=base_price,
            target_price=target_price,
            min_viable_price=min_viable_price,
            market_data=market_data,
            desired_margin=desired_margin
        )
        
        # Step 5: Calculate achieved margin
        margin_achieved = self._calculate_margin(base_price, recommended_price)
        
        # Step 6: Calculate market position
        position_desc = self._describe_market_position(
            recommended_price,
            market_data.median_price
        )
        
        decision = PricingDecision(
            recommended_price=recommended_price,
            strategy=strategy,
            confidence=confidence,
            margin_achieved=margin_achieved,
            market_position=position_desc
        )
        
        logger.info(
            f"Decision: ₹{recommended_price:.2f} ({strategy}), "
            f"margin={margin_achieved:.1f}%, {position_desc}"
        )
        
        return decision
    
    def _calculate_min_price(self, base_price: float, min_margin: float) -> float:
        """Calculate minimum viable price to maintain min margin"""
        return base_price * (1 + min_margin / 100)
    
    def _calculate_target_price(self, base_price: float, desired_margin: float) -> float:
        """Calculate target price with desired margin"""
        return base_price * (1 + desired_margin / 100)
    
    def _calculate_margin(self, base_price: float, selling_price: float) -> float:
        """Calculate margin percentage"""
        if base_price <= 0:
            return 0.0
        return ((selling_price - base_price) / base_price) * 100
    
    def _analyze_market_position(
        self,
        price: float,
        median: float,
        min_price: float,
        max_price: float
    ) -> str:
        """Determine where price falls in market range"""
        if price < median * 0.9:
            return "aggressive_low"
        elif price < median * 0.98:
            return "competitive_low"
        elif price <= median * 1.02:
            return "neutral"
        elif price <= median * 1.1:
            return "premium_mild"
        else:
            return "premium_high"
    
    def _choose_strategy(
        self,
        base_price: float,
        target_price: float,
        min_viable_price: float,
        market_data: CleanedMarketData,
        desired_margin: float
    ) -> Tuple[float, str, str]:
        """
        Core decision logic - THIS IS WHERE THE MAGIC HAPPENS
        
        Returns:
            (recommended_price, strategy_name, confidence_level)
        """
        median = market_data.median_price
        
        # CASE 1: Market median is below our minimum viable price
        # This is a RED FLAG situation
        if median < min_viable_price:
            logger.warning(
                f"Market median (₹{median:.2f}) below minimum viable (₹{min_viable_price:.2f})"
            )
            
            # Can we still compete with minimum margin?
            if median >= base_price * 1.05:
                # Market allows 5% margin, take it
                recommended = round(median * 0.98, 2)  # Slightly below median
                return (
                    recommended,
                    "Competitive Entry Pricing",
                    "Medium"
                )
            else:
                # Market doesn't support viable margins
                return (
                    min_viable_price,
                    "Warning: Market Too Low",
                    "Low"
                )
        
        # CASE 2: Target price fits well in market
        # This is the IDEAL scenario
        if min_viable_price <= target_price <= median * 1.1:
            # We can achieve desired margin and stay competitive
            
            if target_price <= median:
                # Target is at or below median - PERFECT
                recommended = target_price
                strategy = "Competitive Entry Pricing"
                confidence = "High"
            else:
                # Target is slightly above median - still OK
                recommended = target_price
                strategy = "Neutral Market Pricing"
                confidence = "High"
            
            return (recommended, strategy, confidence)
        
        # CASE 3: Target price is below market (high margin possible)
        # OPPORTUNITY to be competitive OR maximize margin
        if target_price < median * 0.9:
            
            if self.aggressive_mode:
                # Go aggressive - match target, gain market share
                recommended = target_price
                strategy = "Competitive Entry Pricing"
                confidence = "High"
            else:
                # Take middle ground - better than median but maximize margin
                # Price at 95% of median
                recommended = round(median * 0.95, 2)
                strategy = "Competitive Entry Pricing"
                confidence = "High"
            
            return (recommended, strategy, confidence)
        
        # CASE 4: Target price is way above market
        # Need to COMPROMISE
        if target_price > median * 1.2:
            logger.warning(
                f"Target price (₹{target_price:.2f}) is {(target_price/median - 1)*100:.0f}% "
                f"above market median"
            )
            
            # Check if premium positioning is viable
            if market_data.max_price >= target_price * 0.95:
                # Some products are priced high - we can try premium
                recommended = round(median * 1.1, 2)
                strategy = "Premium Positioning"
                confidence = "Medium"
            else:
                # Market doesn't support premium pricing
                # Recommend neutral pricing with reduced margin
                recommended = round(median * 1.02, 2)
                strategy = "Neutral Market Pricing"
                confidence = "Medium"
            
            return (recommended, strategy, confidence)
        
        # CASE 5: Default - neutral pricing
        recommended = round(median, 2)
        strategy = "Neutral Market Pricing"
        confidence = "Medium"
        
        return (recommended, strategy, confidence)
    
    def _describe_market_position(self, price: float, median: float) -> str:
        """Generate human-readable market position description"""
        diff_pct = ((price - median) / median) * 100
        
        if abs(diff_pct) < 2:
            return "at market median"
        elif diff_pct < 0:
            return f"{abs(diff_pct):.1f}% below median"
        else:
            return f"{diff_pct:.1f}% above median"
    
    def validate_recommendation(
        self,
        decision: PricingDecision,
        base_price: float
    ) -> Tuple[bool, str]:
        """
        Validate that recommendation is sensible
        
        Returns:
            (is_valid, warning_message)
        """
        # Check margin
        if decision.margin_achieved < self.MIN_ACCEPTABLE_MARGIN:
            return (
                False,
                f"Margin too low ({decision.margin_achieved:.1f}%). "
                f"Minimum acceptable: {self.MIN_ACCEPTABLE_MARGIN}%"
            )
        
        # Warn if margin is below desired threshold
        if decision.margin_achieved < self.WARNING_MARGIN:
            return (
                True,
                f"⚠️ Margin ({decision.margin_achieved:.1f}%) below "
                f"recommended threshold ({self.WARNING_MARGIN}%)"
            )
        
        # Check price is reasonable
        if decision.recommended_price < base_price:
            return (False, "Recommended price is below base price!")
        
        return (True, "")


# ===== USAGE EXAMPLE =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Mock market data
    market = CleanedMarketData(
        clean_prices=[1899, 1949, 1999, 2049, 2099, 2149],
        median_price=1999,
        min_price=1899,
        max_price=2149,
        avg_price=2024,
        product_count=6
    )
    
    agent = PricingStrategyAgent(aggressive_mode=False)
    
    # Test scenarios
    scenarios = [
        {"base": 1500, "margin": 20, "desc": "Good margin possible"},
        {"base": 1700, "margin": 15, "desc": "Moderate margin"},
        {"base": 1900, "margin": 10, "desc": "Tight margin"},
        {"base": 1800, "margin": 30, "desc": "High margin target"},
    ]
    
    for scenario in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario['desc']}")
        print(f"Base: ₹{scenario['base']}, Desired Margin: {scenario['margin']}%")
        
        decision = agent.compute_pricing_decision(
            market,
            scenario['base'],
            scenario['margin']
        )
        
        print(f"\nRecommendation: ₹{decision.recommended_price}")
        print(f"Strategy: {decision.strategy}")
        print(f"Confidence: {decision.confidence}")
        print(f"Margin Achieved: {decision.margin_achieved:.1f}%")
        print(f"Position: {decision.market_position}")
        
        valid, msg = agent.validate_recommendation(decision, scenario['base'])
        if msg:
            print(f"Validation: {msg}")
