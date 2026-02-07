"""
Pricing Strategy Agent

Purpose: Perform ALL numeric reasoning for the negotiation.
This agent is DETERMINISTIC and RULE-BASED. No LLM involved.

Responsibilities:
- Compute next offer
- Decide acceptance or rejection
- Enforce hard constraints
- Track concession budget
"""
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from typing import Optional, List, Tuple

from ..models import (
    ProductData,
    InventoryContext,
    StrategicControls,
    BuyerOffer,
    PricingDecision,
    NegotiationMode,
    OfferDecision,
)
from .context_agent import StrategicPosture


@dataclass
class PricingState:
    """Mutable state tracking for a negotiation session."""
    
    current_round: int
    current_offer: Decimal        # Our last offer
    buyer_last_offer: Optional[Decimal]
    concession_used: Decimal      # Total concession given so far
    offers_history: List[Decimal]  # History of our offers
    buyer_history: List[Decimal]   # History of buyer offers
    
    def __post_init__(self):
        if not isinstance(self.concession_used, Decimal):
            self.concession_used = Decimal(str(self.concession_used))


class PricingStrategyAgent:
    """
    Deterministic pricing engine.
    
    This agent:
    - Never invents prices
    - Never violates seller constraints
    - Is fully auditable
    - Makes no use of language models
    """
    
    def __init__(self):
        # Minimum acceptable concession movement from buyer
        self.min_buyer_movement_pct = Decimal("0.02")  # 2%
    
    def compute_initial_offer(
        self,
        product: ProductData,
        inventory: InventoryContext,
        posture: StrategicPosture,
    ) -> Decimal:
        """
        Compute the seller's opening offer.
        
        This is typically at or near the target price.
        """
        base = product.base_price
        target = posture.target_price
        
        # Start at target or slightly above based on aggressiveness
        if posture.aggressiveness >= Decimal("0.7"):
            # Very aggressive: start at base price
            initial = base
        elif posture.aggressiveness >= Decimal("0.4"):
            # Moderate: start between base and target
            initial = target + (base - target) * Decimal("0.3")
        else:
            # Conservative: start at target
            initial = target
        
        # Apply quantity discount if applicable
        if inventory.requested_quantity > 1:
            initial = initial * posture.quantity_discount_factor
        
        return self._round_price(initial)
    
    def evaluate_offer(
        self,
        buyer_offer: BuyerOffer,
        product: ProductData,
        inventory: InventoryContext,
        strategy: StrategicControls,
        posture: StrategicPosture,
        state: PricingState,
    ) -> PricingDecision:
        """
        Evaluate a buyer's offer and decide response.
        
        Returns a fully computed PricingDecision.
        """
        offered = buyer_offer.offered_price
        quantity = buyer_offer.offered_quantity or inventory.requested_quantity
        
        # Check hard constraints first
        violations = self._check_constraints(
            offered, product, inventory, strategy, posture
        )
        
        if violations:
            # Constraint violation - must reject or counter firmly
            return self._handle_constraint_violation(
                offered, violations, product, quantity, posture, state, strategy
            )
        
        # Compute metrics
        margin_pct, profit_unit, total_profit = self._compute_metrics(
            offered, product.cost_price, quantity
        )
        
        # Decide action based on comparison to our targets
        decision, counter_price = self._make_decision(
            offered, product, posture, state, strategy
        )
        
        # Compute remaining budget
        remaining_budget = posture.total_concession_budget - state.concession_used
        budget_used_pct = (state.concession_used / posture.total_concession_budget * 100
                          if posture.total_concession_budget > 0 else Decimal("100"))
        
        # Calculate concession if we're countering
        concession_made = Decimal("0")
        if decision == OfferDecision.COUNTER and counter_price:
            concession_made = state.current_offer - counter_price
        
        return PricingDecision(
            decision=decision,
            counter_offer_price=counter_price if decision == OfferDecision.COUNTER else None,
            accepted_price=offered if decision == OfferDecision.ACCEPT else None,
            margin_percentage=margin_pct,
            profit_per_unit=profit_unit,
            total_profit=total_profit,
            within_constraints=len(violations) == 0,
            constraint_violations=violations,
            concession_made=concession_made,
            remaining_concession_budget=max(Decimal("0"), remaining_budget - concession_made),
            concession_percentage_used=min(Decimal("100"), budget_used_pct),
        )
    
    def _check_constraints(
        self,
        offered_price: Decimal,
        product: ProductData,
        inventory: InventoryContext,
        strategy: StrategicControls,
        posture: StrategicPosture,
    ) -> List[str]:
        """Check if offer violates any hard constraints."""
        violations = []
        
        # Check against walk-away price
        if offered_price < posture.walk_away_price:
            violations.append(
                f"Offer {offered_price} below walk-away price {posture.walk_away_price}"
            )
        
        # Check against min acceptable price
        if offered_price < product.min_acceptable_price:
            violations.append(
                f"Offer {offered_price} below minimum acceptable {product.min_acceptable_price}"
            )
        
        # In MAX_PROFIT mode, check against cost (no loss allowed)
        if strategy.mode == NegotiationMode.MAX_PROFIT:
            if offered_price < product.cost_price:
                violations.append(
                    f"Offer {offered_price} below cost {product.cost_price} in MAX_PROFIT mode"
                )
        
        # In MIN_LOSS mode, check max loss
        if strategy.mode == NegotiationMode.MIN_LOSS:
            if product.cost_price > Decimal("0"):
                loss_pct = ((product.cost_price - offered_price) / product.cost_price * 100)
                if loss_pct > product.max_loss_percentage:
                    violations.append(
                        f"Loss {loss_pct:.1f}% exceeds max allowed {product.max_loss_percentage}%"
                    )
        
        return violations
    
    def _handle_constraint_violation(
        self,
        offered: Decimal,
        violations: List[str],
        product: ProductData,
        quantity: int,
        posture: StrategicPosture,
        state: PricingState,
        strategy: StrategicControls,
    ) -> PricingDecision:
        """Handle an offer that violates constraints."""
        # Compute metrics at the offered price (for reporting)
        margin_pct, profit_unit, total_profit = self._compute_metrics(
            offered, product.cost_price, quantity
        )
        
        remaining_budget = posture.total_concession_budget - state.concession_used
        budget_used_pct = (state.concession_used / posture.total_concession_budget * 100
                          if posture.total_concession_budget > 0 else Decimal("100"))
        
        # If we're out of rounds, reject
        if state.current_round >= strategy.max_rounds:
            return PricingDecision(
                decision=OfferDecision.REJECT,
                counter_offer_price=None,
                accepted_price=None,
                margin_percentage=margin_pct,
                profit_per_unit=profit_unit,
                total_profit=total_profit,
                within_constraints=False,
                constraint_violations=violations,
                concession_made=Decimal("0"),
                remaining_concession_budget=remaining_budget,
                concession_percentage_used=budget_used_pct,
            )
        
        # Otherwise, counter with our reservation price
        counter = posture.reservation_price
        
        return PricingDecision(
            decision=OfferDecision.COUNTER,
            counter_offer_price=self._round_price(counter),
            accepted_price=None,
            margin_percentage=margin_pct,
            profit_per_unit=profit_unit,
            total_profit=total_profit,
            within_constraints=False,
            constraint_violations=violations,
            concession_made=max(Decimal("0"), state.current_offer - counter),
            remaining_concession_budget=remaining_budget,
            concession_percentage_used=budget_used_pct,
        )
    
    def _make_decision(
        self,
        offered: Decimal,
        product: ProductData,
        posture: StrategicPosture,
        state: PricingState,
        strategy: StrategicControls,
    ) -> Tuple[OfferDecision, Optional[Decimal]]:
        """
        Make the core pricing decision.
        
        Returns (decision, counter_price or None).
        """
        target = posture.target_price
        reservation = posture.reservation_price
        
        # ACCEPT if at or above target
        if offered >= target:
            return OfferDecision.ACCEPT, None
        
        # ACCEPT if at or above reservation and we're flexible
        if offered >= reservation:
            # Check if buyer is moving enough
            if self._is_buyer_moving_enough(offered, state):
                return OfferDecision.ACCEPT, None
            # Accept if we're in late rounds
            if state.current_round >= strategy.max_rounds - 1:
                return OfferDecision.ACCEPT, None
            # Accept in MIN_LOSS mode at reservation
            if strategy.mode == NegotiationMode.MIN_LOSS:
                return OfferDecision.ACCEPT, None
        
        # COUNTER with a new offer
        remaining_budget = posture.total_concession_budget - state.concession_used
        
        if remaining_budget <= 0:
            # No budget left - hold firm
            return OfferDecision.COUNTER, state.current_offer
        
        # Compute concession for this round
        concession = self._compute_concession(
            state, posture, strategy, offered
        )
        
        new_offer = state.current_offer - concession
        
        # Never go below reservation
        new_offer = max(new_offer, reservation)
        
        return OfferDecision.COUNTER, self._round_price(new_offer)
    
    def _compute_concession(
        self,
        state: PricingState,
        posture: StrategicPosture,
        strategy: StrategicControls,
        buyer_offered: Decimal,
    ) -> Decimal:
        """
        Compute how much to concede this round.
        
        Concession strategy varies by mode and round.
        """
        base_concession = posture.per_round_concession
        
        # Adjust based on buyer's movement
        if state.buyer_last_offer is not None:
            buyer_movement = buyer_offered - state.buyer_last_offer
            
            if buyer_movement <= 0:
                # Buyer didn't move up - reduce our concession
                base_concession *= Decimal("0.3")
            elif buyer_movement < base_concession:
                # Buyer moved less than us - match their movement
                base_concession = buyer_movement * Decimal("0.8")
        
        # Reduce concession in early rounds for MAX_PROFIT
        if strategy.mode == NegotiationMode.MAX_PROFIT:
            if state.current_round <= 2:
                base_concession *= Decimal("0.5")
        
        # Increase in late rounds for MIN_LOSS
        if strategy.mode == NegotiationMode.MIN_LOSS:
            if state.current_round >= strategy.max_rounds - 2:
                base_concession *= Decimal("1.5")
        
        # Never concede more than remaining budget
        remaining = posture.total_concession_budget - state.concession_used
        return min(base_concession, remaining)
    
    def _is_buyer_moving_enough(
        self,
        current_offer: Decimal,
        state: PricingState,
    ) -> bool:
        """Check if buyer is making meaningful progress."""
        if state.buyer_last_offer is None:
            return True
        
        movement = current_offer - state.buyer_last_offer
        
        if state.buyer_last_offer > 0:
            movement_pct = movement / state.buyer_last_offer
            return movement_pct >= self.min_buyer_movement_pct
        
        return movement > 0
    
    def _compute_metrics(
        self,
        price: Decimal,
        cost: Decimal,
        quantity: int,
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """Compute margin %, profit per unit, total profit."""
        profit_unit = price - cost
        total_profit = profit_unit * quantity
        
        if price > 0:
            margin_pct = (profit_unit / price * 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            margin_pct = Decimal("0")
        
        return margin_pct, profit_unit, total_profit
    
    def _round_price(self, price: Decimal) -> Decimal:
        """Round price to 2 decimal places."""
        return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
