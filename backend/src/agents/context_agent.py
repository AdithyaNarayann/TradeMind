"""
Context Analysis Agent

Purpose: Interpret seller inputs into strategic posture.
This agent performs NO negotiation - only analysis.

Outputs:
- Aggressiveness score (0-1)
- Concession budget
- Preferred closing round
- Risk tolerance level
"""
from decimal import Decimal
from dataclasses import dataclass
from typing import Tuple

from ..models import (
    ProductData,
    InventoryContext,
    StrategicControls,
    NegotiationMode,
    PressureLevel,
    FrequencyLevel,
    UrgencyLevel,
    RelationshipPriority,
)


@dataclass
class StrategicPosture:
    """Computed strategic posture for the negotiation session."""
    
    # Core metrics (0.0 to 1.0)
    aggressiveness: Decimal      # How firmly to defend price
    flexibility: Decimal         # How willing to make concessions
    risk_tolerance: Decimal      # Willingness to walk away
    
    # Computed targets
    target_price: Decimal        # Ideal closing price
    reservation_price: Decimal   # Minimum acceptable price
    walk_away_price: Decimal     # Below this, walk away
    
    # Concession strategy
    total_concession_budget: Decimal    # Max $ we can concede
    per_round_concession: Decimal       # Suggested concession per round
    preferred_closing_round: int        # Ideal round to close deal
    
    # Quantity adjustments
    quantity_discount_factor: Decimal   # Discount for volume
    
    def __post_init__(self):
        """Ensure all values are Decimal type."""
        for field in ['aggressiveness', 'flexibility', 'risk_tolerance']:
            val = getattr(self, field)
            if not isinstance(val, Decimal):
                setattr(self, field, Decimal(str(val)))


class ContextAnalysisAgent:
    """
    Analyzes seller inputs to produce a strategic negotiation posture.
    
    This agent is stateless and deterministic.
    Given identical inputs, it always produces identical outputs.
    """
    
    # Weight factors for computing aggressiveness
    URGENCY_WEIGHTS = {
        UrgencyLevel.LOW: Decimal("0.9"),
        UrgencyLevel.MEDIUM: Decimal("0.6"),
        UrgencyLevel.HIGH: Decimal("0.3"),
    }
    
    INVENTORY_PRESSURE_WEIGHTS = {
        PressureLevel.LOW: Decimal("0.9"),
        PressureLevel.MEDIUM: Decimal("0.6"),
        PressureLevel.HIGH: Decimal("0.3"),
    }
    
    SALES_FREQUENCY_WEIGHTS = {
        FrequencyLevel.LOW: Decimal("0.7"),    # Rare item = be aggressive
        FrequencyLevel.MEDIUM: Decimal("0.5"),
        FrequencyLevel.HIGH: Decimal("0.3"),   # Common item = more flexible
    }
    
    RELATIONSHIP_WEIGHTS = {
        RelationshipPriority.LOW: Decimal("0.9"),
        RelationshipPriority.MEDIUM: Decimal("0.6"),
        RelationshipPriority.HIGH: Decimal("0.3"),
    }
    
    def analyze(
        self,
        product: ProductData,
        inventory: InventoryContext,
        strategy: StrategicControls,
    ) -> StrategicPosture:
        """
        Analyze inputs and produce strategic posture.
        
        This is the main entry point for context analysis.
        """
        # Compute base metrics
        aggressiveness = self._compute_aggressiveness(inventory, strategy)
        flexibility = self._compute_flexibility(strategy)
        risk_tolerance = self._compute_risk_tolerance(strategy, inventory)
        
        # Compute price targets
        target_price, reservation_price, walk_away_price = self._compute_price_targets(
            product, strategy, aggressiveness
        )
        
        # Compute concession strategy
        concession_budget = self._compute_concession_budget(
            product, target_price, reservation_price
        )
        per_round_concession = self._compute_per_round_concession(
            concession_budget, strategy.max_rounds, strategy
        )
        preferred_round = self._compute_preferred_closing_round(strategy)
        
        # Compute quantity factor
        quantity_factor = self._compute_quantity_discount(
            inventory, product, strategy
        )
        
        return StrategicPosture(
            aggressiveness=aggressiveness,
            flexibility=flexibility,
            risk_tolerance=risk_tolerance,
            target_price=target_price,
            reservation_price=reservation_price,
            walk_away_price=walk_away_price,
            total_concession_budget=concession_budget,
            per_round_concession=per_round_concession,
            preferred_closing_round=preferred_round,
            quantity_discount_factor=quantity_factor,
        )
    
    def _compute_aggressiveness(
        self,
        inventory: InventoryContext,
        strategy: StrategicControls,
    ) -> Decimal:
        """
        Compute how aggressively to defend price.
        
        High aggressiveness = fewer/smaller concessions, willing to walk away.
        Low aggressiveness = more flexible, prioritize closing.
        """
        # Mode is primary factor
        if strategy.mode == NegotiationMode.MAX_PROFIT:
            base = Decimal("0.8")
        else:
            base = Decimal("0.4")
        
        # Adjust for urgency (high urgency = less aggressive)
        urgency_factor = self.URGENCY_WEIGHTS[strategy.urgency]
        
        # Adjust for inventory pressure
        inventory_factor = self.INVENTORY_PRESSURE_WEIGHTS[inventory.inventory_pressure]
        
        # Weighted average
        aggressiveness = (base * Decimal("0.5") + 
                         urgency_factor * Decimal("0.25") +
                         inventory_factor * Decimal("0.25"))
        
        return min(Decimal("1.0"), max(Decimal("0.1"), aggressiveness))
    
    def _compute_flexibility(self, strategy: StrategicControls) -> Decimal:
        """Compute willingness to make concessions."""
        if strategy.mode == NegotiationMode.MIN_LOSS:
            base = Decimal("0.7")
        else:
            base = Decimal("0.3")
        
        # Relationship priority affects flexibility
        relationship_factor = Decimal("1.0") - self.RELATIONSHIP_WEIGHTS[strategy.relationship_priority]
        
        flexibility = base + (relationship_factor * Decimal("0.2"))
        return min(Decimal("1.0"), max(Decimal("0.1"), flexibility))
    
    def _compute_risk_tolerance(
        self,
        strategy: StrategicControls,
        inventory: InventoryContext,
    ) -> Decimal:
        """
        Compute willingness to walk away from deal.
        
        High risk tolerance = willing to lose deal for better margin.
        Low risk tolerance = prioritize closing at any reasonable price.
        """
        if strategy.mode == NegotiationMode.MAX_PROFIT:
            base = Decimal("0.7")
        else:
            base = Decimal("0.3")
        
        # High inventory pressure reduces risk tolerance
        if inventory.inventory_pressure == PressureLevel.HIGH:
            base -= Decimal("0.2")
        
        # High urgency reduces risk tolerance
        if strategy.urgency == UrgencyLevel.HIGH:
            base -= Decimal("0.2")
        
        return min(Decimal("1.0"), max(Decimal("0.1"), base))
    
    def _compute_price_targets(
        self,
        product: ProductData,
        strategy: StrategicControls,
        aggressiveness: Decimal,
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Compute target, reservation, and walk-away prices.
        
        These form a price ladder that guides the negotiation.
        """
        base = product.base_price
        cost = product.cost_price
        floor = product.min_acceptable_price
        
        # Target price: where we want to close
        # More aggressive = closer to base price
        margin = base - cost
        target_discount = margin * (Decimal("1.0") - aggressiveness) * Decimal("0.3")
        target = base - target_discount
        
        # Reservation price: our internal minimum
        # This is what we'd grudgingly accept
        if strategy.mode == NegotiationMode.MAX_PROFIT:
            # In MAX_PROFIT, reservation is well above floor
            reservation = floor + (target - floor) * Decimal("0.3")
        else:
            # In MIN_LOSS, reservation can be at floor
            reservation = floor
        
        # Walk-away price: absolute minimum, may allow loss in MIN_LOSS
        if strategy.mode == NegotiationMode.MIN_LOSS and product.max_loss_percentage > 0:
            max_loss = cost * (product.max_loss_percentage / Decimal("100"))
            walk_away = cost - max_loss
        else:
            walk_away = floor
        
        # Ensure hierarchy
        target = max(target, reservation)
        reservation = max(reservation, walk_away)
        
        return target, reservation, walk_away
    
    def _compute_concession_budget(
        self,
        product: ProductData,
        target_price: Decimal,
        reservation_price: Decimal,
    ) -> Decimal:
        """Compute total concession budget in dollars."""
        return target_price - reservation_price
    
    def _compute_per_round_concession(
        self,
        total_budget: Decimal,
        max_rounds: int,
        strategy: StrategicControls,
    ) -> Decimal:
        """
        Compute suggested concession per round.
        
        In MAX_PROFIT mode: back-loaded (smaller early, bigger late)
        In MIN_LOSS mode: more uniform distribution
        """
        if max_rounds <= 1:
            return total_budget
        
        # Reserve some budget for later rounds
        if strategy.mode == NegotiationMode.MAX_PROFIT:
            # Use less budget early
            effective_rounds = max_rounds + 2  # Spread thinner
        else:
            effective_rounds = max_rounds
        
        return total_budget / Decimal(str(effective_rounds))
    
    def _compute_preferred_closing_round(self, strategy: StrategicControls) -> int:
        """Compute ideal round to close deal."""
        max_rounds = strategy.max_rounds
        
        if strategy.mode == NegotiationMode.MAX_PROFIT:
            # Don't rush in MAX_PROFIT - let buyer come up
            return min(3, max_rounds)
        else:
            # Close faster in MIN_LOSS
            return min(2, max_rounds)
    
    def _compute_quantity_discount(
        self,
        inventory: InventoryContext,
        product: ProductData,
        strategy: StrategicControls,
    ) -> Decimal:
        """
        Compute per-unit discount factor for bulk orders.
        
        Returns a multiplier (e.g., 0.95 = 5% discount for volume).
        """
        requested = inventory.requested_quantity
        available = inventory.available_quantity
        
        # Base discount for buying large portion of inventory
        ratio = Decimal(str(requested)) / Decimal(str(available))
        
        if ratio >= Decimal("0.8"):
            # Buying 80%+ of stock
            base_discount = Decimal("0.08")  # Up to 8%
        elif ratio >= Decimal("0.5"):
            base_discount = Decimal("0.05")  # Up to 5%
        elif ratio >= Decimal("0.25"):
            base_discount = Decimal("0.03")  # Up to 3%
        else:
            base_discount = Decimal("0.0")
        
        # Reduce discount in MAX_PROFIT mode
        if strategy.mode == NegotiationMode.MAX_PROFIT:
            base_discount *= Decimal("0.5")
        
        # Never discount below margin
        margin_percentage = (product.base_price - product.cost_price) / product.base_price
        if base_discount > margin_percentage * Decimal("0.5"):
            base_discount = margin_percentage * Decimal("0.5")
        
        return Decimal("1.0") - base_discount
