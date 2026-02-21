"""
Tests for the Negotiation Engine.

Run with: pytest tests/ -v
"""
import pytest
from decimal import Decimal

from app.models import (
    ProductData,
    InventoryContext,
    StrategicControls,
    NegotiationMode,
    PressureLevel,
    FrequencyLevel,
    UrgencyLevel,
    RelationshipPriority,
)
from app.agents import ContextAnalysisAgent, PricingStrategyAgent


class TestContextAnalysisAgent:
    """Tests for the Context Analysis Agent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ContextAnalysisAgent()
        
        self.product = ProductData(
            product_id="TEST-001",
            product_name="Test Product",
            base_price=Decimal("100.00"),
            cost_price=Decimal("60.00"),
            min_acceptable_price=Decimal("75.00"),
            max_loss_percentage=Decimal("0"),
        )
        
        self.inventory = InventoryContext(
            available_quantity=100,
            requested_quantity=10,
            inventory_pressure=PressureLevel.MEDIUM,
            sales_frequency=FrequencyLevel.MEDIUM,
        )
    
    def test_max_profit_mode_produces_high_aggressiveness(self):
        """MAX_PROFIT mode should produce higher aggressiveness."""
        strategy = StrategicControls(
            mode=NegotiationMode.MAX_PROFIT,
            urgency=UrgencyLevel.LOW,
            relationship_priority=RelationshipPriority.LOW,
            max_rounds=5,
        )
        
        posture = self.agent.analyze(self.product, self.inventory, strategy)
        
        assert posture.aggressiveness >= Decimal("0.6")
        assert posture.target_price >= posture.reservation_price
        assert posture.reservation_price >= posture.walk_away_price
    
    def test_min_loss_mode_produces_lower_aggressiveness(self):
        """MIN_LOSS mode should produce lower aggressiveness."""
        strategy = StrategicControls(
            mode=NegotiationMode.MIN_LOSS,
            urgency=UrgencyLevel.HIGH,
            relationship_priority=RelationshipPriority.HIGH,
            max_rounds=5,
        )
        
        posture = self.agent.analyze(self.product, self.inventory, strategy)
        
        assert posture.aggressiveness <= Decimal("0.5")
        assert posture.flexibility >= Decimal("0.5")
    
    def test_price_hierarchy_is_maintained(self):
        """Prices should follow: target >= reservation >= walk_away."""
        strategy = StrategicControls(mode=NegotiationMode.MAX_PROFIT)
        
        posture = self.agent.analyze(self.product, self.inventory, strategy)
        
        assert posture.target_price >= posture.reservation_price
        assert posture.reservation_price >= posture.walk_away_price
        assert posture.walk_away_price >= self.product.min_acceptable_price
    
    def test_concession_budget_is_positive(self):
        """Concession budget should be non-negative."""
        strategy = StrategicControls(mode=NegotiationMode.MAX_PROFIT)
        
        posture = self.agent.analyze(self.product, self.inventory, strategy)
        
        assert posture.total_concession_budget >= Decimal("0")
        assert posture.per_round_concession >= Decimal("0")


class TestPricingStrategyAgent:
    """Tests for the Pricing Strategy Agent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = PricingStrategyAgent()
        self.context_agent = ContextAnalysisAgent()
        
        self.product = ProductData(
            product_id="TEST-001",
            product_name="Test Product",
            base_price=Decimal("100.00"),
            cost_price=Decimal("60.00"),
            min_acceptable_price=Decimal("75.00"),
            max_loss_percentage=Decimal("0"),
        )
        
        self.inventory = InventoryContext(
            available_quantity=100,
            requested_quantity=10,
        )
        
        self.strategy = StrategicControls(
            mode=NegotiationMode.MAX_PROFIT,
            max_rounds=5,
        )
        
        self.posture = self.context_agent.analyze(
            self.product, self.inventory, self.strategy
        )
    
    def test_initial_offer_above_cost(self):
        """Initial offer should be above cost price."""
        offer = self.agent.compute_initial_offer(
            self.product, self.inventory, self.posture
        )
        
        assert offer > self.product.cost_price
        assert offer <= self.product.base_price
    
    def test_initial_offer_respects_target(self):
        """Initial offer should be at or above target price."""
        offer = self.agent.compute_initial_offer(
            self.product, self.inventory, self.posture
        )
        
        # Initial offer should be near target or higher
        assert offer >= self.posture.target_price * Decimal("0.95")


class TestPriceValidation:
    """Tests for Pydantic model validation."""
    
    def test_min_price_cannot_exceed_base(self):
        """min_acceptable_price cannot be above base_price."""
        with pytest.raises(ValueError):
            ProductData(
                product_id="TEST-001",
                product_name="Test Product",
                base_price=Decimal("100.00"),
                cost_price=Decimal("60.00"),
                min_acceptable_price=Decimal("150.00"),  # Invalid
            )
    
    def test_quantity_cannot_exceed_available(self):
        """requested_quantity cannot exceed available_quantity."""
        with pytest.raises(ValueError):
            InventoryContext(
                available_quantity=10,
                requested_quantity=20,  # Invalid
            )
    
    def test_valid_product_data(self):
        """Valid product data should pass validation."""
        product = ProductData(
            product_id="TEST-001",
            product_name="Test Product",
            base_price=Decimal("100.00"),
            cost_price=Decimal("60.00"),
            min_acceptable_price=Decimal("75.00"),
        )
        
        assert product.base_price == Decimal("100.00")
        assert product.cost_price == Decimal("60.00")
