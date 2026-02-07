"""
AGENT 5: Insight Generator Agent
Purpose: Translate analytics into seller-friendly insights
Type: LLM-based language agent
"""
import logging
from typing import List, Optional

from models.schemas import CleanedMarketData, PricingDecision

logger = logging.getLogger(__name__)


class InsightGeneratorAgent:
    """
    Generates human-readable, actionable insights from pricing decisions
    Builds trust and makes output explainable
    """
    
    def __init__(self, llm_client=None, use_llm: bool = True):
        """
        Args:
            llm_client: OpenAI client (optional)
            use_llm: Whether to use LLM for advanced insights
        """
        self.llm_client = llm_client
        self.use_llm = use_llm and llm_client is not None
    
    def generate_insights(
        self,
        decision: PricingDecision,
        market_data: CleanedMarketData,
        base_price: float,
        desired_margin: float
    ) -> tuple[str, List[str]]:
        """
        Generate primary insight and supporting reasoning
        
        Args:
            decision: Pricing decision from strategy agent
            market_data: Market statistics
            base_price: Seller's base price
            desired_margin: Seller's target margin
            
        Returns:
            (primary_insight, reasoning_points)
        """
        if self.use_llm:
            return self._generate_llm_insights(
                decision, market_data, base_price, desired_margin
            )
        else:
            return self._generate_rule_based_insights(
                decision, market_data, base_price, desired_margin
            )
    
    def _generate_rule_based_insights(
        self,
        decision: PricingDecision,
        market_data: CleanedMarketData,
        base_price: float,
        desired_margin: float
    ) -> tuple[str, List[str]]:
        """
        Generate insights using rules and templates
        Fast, reliable, no API calls
        """
        # Primary insight
        primary = self._build_primary_insight(decision, market_data)
        
        # Supporting reasoning
        reasoning = self._build_reasoning_points(
            decision, market_data, base_price, desired_margin
        )
        
        return (primary, reasoning)
    
    def _build_primary_insight(
        self,
        decision: PricingDecision,
        market_data: CleanedMarketData
    ) -> str:
        """Build the main insight sentence"""
        
        price = decision.recommended_price
        median = market_data.median_price
        strategy = decision.strategy
        
        # Template based on strategy
        if strategy == "Competitive Entry Pricing":
            insight = (
                f"Pricing at ₹{price:,.0f} positions you competitively "
                f"in a market where most sellers price around ₹{median:,.0f}. "
                f"This gives you a strong entry point while maintaining healthy margins."
            )
        
        elif strategy == "Neutral Market Pricing":
            insight = (
                f"At ₹{price:,.0f}, you're aligned with the market median of ₹{median:,.0f}. "
                f"This balanced approach maintains your desired margin while staying competitive."
            )
        
        elif strategy == "Premium Positioning":
            insight = (
                f"Pricing at ₹{price:,.0f} positions you above the market median (₹{median:,.0f}), "
                f"which can work if you differentiate through quality, service, or brand value."
            )
        
        elif strategy == "Warning: Market Too Low":
            insight = (
                f"⚠️ The market median (₹{median:,.0f}) is below your minimum viable price. "
                f"At ₹{price:,.0f}, you maintain minimum margins, but consider if this market is worth entering."
            )
        
        else:
            insight = (
                f"Based on market analysis of {market_data.product_count} competitors, "
                f"₹{price:,.0f} is recommended for this product."
            )
        
        return insight
    
    def _build_reasoning_points(
        self,
        decision: PricingDecision,
        market_data: CleanedMarketData,
        base_price: float,
        desired_margin: float
    ) -> List[str]:
        """Build bullet points explaining the reasoning"""
        
        points = []
        
        # Point 1: Market context
        points.append(
            f"Market analysis: {market_data.product_count} comparable products "
            f"ranging from ₹{market_data.min_price:,.0f} to ₹{market_data.max_price:,.0f}"
        )
        
        # Point 2: Margin achievement
        margin_diff = decision.margin_achieved - desired_margin
        if abs(margin_diff) < 1:
            margin_msg = f"Achieves your target margin of {desired_margin:.1f}%"
        elif margin_diff > 0:
            margin_msg = f"Exceeds target margin: {decision.margin_achieved:.1f}% vs target {desired_margin:.1f}%"
        else:
            margin_msg = f"Margin: {decision.margin_achieved:.1f}% (target was {desired_margin:.1f}%)"
        points.append(margin_msg)
        
        # Point 3: Competitive position
        points.append(
            f"Your position: {decision.market_position} — "
            f"{self._position_explanation(decision.recommended_price, market_data.median_price)}"
        )
        
        # Point 4: Strategy-specific advice
        if decision.strategy == "Competitive Entry Pricing":
            points.append(
                "Pro tip: This competitive pricing can help you gain initial traction "
                "and reviews, which are crucial for long-term success"
            )
        elif decision.strategy == "Premium Positioning":
            points.append(
                "Note: Premium pricing works best with excellent product photos, "
                "detailed descriptions, and strong customer service"
            )
        elif decision.strategy == "Warning: Market Too Low":
            points.append(
                "Consider: Can you reduce costs, or is there a different product category "
                "where margins are healthier?"
            )
        
        return points
    
    def _position_explanation(self, price: float, median: float) -> str:
        """Explain what the market position means"""
        diff_pct = abs(((price - median) / median) * 100)
        
        if price < median * 0.95:
            return "strong competitive advantage on price"
        elif price < median:
            return "slight price advantage over typical competitors"
        elif price <= median * 1.02:
            return "in line with most competitors"
        elif price <= median * 1.1:
            return "positioned as a premium option"
        else:
            return "priced significantly above market average"
    
    def _generate_llm_insights(
        self,
        decision: PricingDecision,
        market_data: CleanedMarketData,
        base_price: float,
        desired_margin: float
    ) -> tuple[str, List[str]]:
        """
        Use LLM to generate more nuanced, natural insights
        Optional enhancement
        """
        try:
            prompt = self._build_llm_prompt(
                decision, market_data, base_price, desired_margin
            )
            
            response = self.llm_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a pricing advisor helping Amazon sellers. "
                                   "Be concise, actionable, and encouraging."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse response (expecting insight + bullet points)
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            
            if len(lines) >= 2:
                primary = lines[0]
                reasoning = [l.lstrip('•-* ') for l in lines[1:] if l]
                return (primary, reasoning)
            else:
                # Fallback to rule-based
                logger.warning("LLM response malformed, using rule-based")
                return self._generate_rule_based_insights(
                    decision, market_data, base_price, desired_margin
                )
                
        except Exception as e:
            logger.error(f"LLM insight generation failed: {e}")
            # Fallback to rule-based
            return self._generate_rule_based_insights(
                decision, market_data, base_price, desired_margin
            )
    
    def _build_llm_prompt(
        self,
        decision: PricingDecision,
        market_data: CleanedMarketData,
        base_price: float,
        desired_margin: float
    ) -> str:
        """Build prompt for LLM"""
        return f"""Generate a pricing insight for an Amazon seller.

RECOMMENDATION:
- Recommended Price: ₹{decision.recommended_price:,.0f}
- Strategy: {decision.strategy}
- Margin Achieved: {decision.margin_achieved:.1f}%
- Target Margin: {desired_margin:.1f}%

MARKET DATA:
- Median Price: ₹{market_data.median_price:,.0f}
- Price Range: ₹{market_data.min_price:,.0f} - ₹{market_data.max_price:,.0f}
- Competitors: {market_data.product_count}
- Market Position: {decision.market_position}

Generate:
1. One compelling sentence explaining the recommendation
2. 3-4 bullet points with specific reasoning and actionable advice

Be specific, encouraging, and data-driven. Use Indian Rupee format."""


# ===== USAGE EXAMPLE =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Mock data
    decision = PricingDecision(
        recommended_price=1949,
        strategy="Competitive Entry Pricing",
        confidence="High",
        margin_achieved=18.5,
        market_position="2.5% below median"
    )
    
    market = CleanedMarketData(
        clean_prices=[1899, 1949, 1999, 2049, 2099],
        median_price=1999,
        min_price=1899,
        max_price=2149,
        avg_price=2019,
        product_count=5
    )
    
    # Test rule-based (no LLM)
    agent = InsightGeneratorAgent(use_llm=False)
    
    insight, reasoning = agent.generate_insights(
        decision=decision,
        market_data=market,
        base_price=1650,
        desired_margin=20
    )
    
    print("PRIMARY INSIGHT:")
    print(insight)
    print("\nREASONING:")
    for i, point in enumerate(reasoning, 1):
        print(f"{i}. {point}")
