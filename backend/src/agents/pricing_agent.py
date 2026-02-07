"""
Pricing Strategy Agent — AI-Powered

Purpose: Perform ALL numeric reasoning for the negotiation using LLM.
The LLM makes strategic decisions (accept/counter/reject + counter price).
Hard constraints are enforced as post-LLM guardrails.
Metrics (margin, profit) are computed deterministically.

Architecture:
1. Send full negotiation context to LLM
2. LLM reasons about optimal decision and returns structured JSON
3. Parse response and enforce hard safety guardrails
4. Compute financial metrics deterministically
5. If LLM fails → fall back to basic heuristic logic
"""
import json
import structlog
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
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
from ..services.llm_client import get_llm_client, OpenRouterClient
from ..services import llm_prompts

logger = structlog.get_logger(__name__)


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
    AI-powered pricing engine.
    
    Uses LLM for strategic decisions while enforcing hard constraints:
    - NEVER accepts below walk_away_price
    - NEVER counters below reservation_price
    - NEVER exceeds concession budget
    - All financial metrics computed deterministically
    
    Falls back to basic heuristics if LLM is unavailable.
    """
    
    def __init__(self, llm_client: Optional[OpenRouterClient] = None):
        self.llm = llm_client or get_llm_client()
        self.min_buyer_movement_pct = Decimal("0.02")  # 2%
    
    def compute_initial_offer(
        self,
        product: ProductData,
        inventory: InventoryContext,
        posture: StrategicPosture,
    ) -> Decimal:
        """
        Compute the seller's opening offer using AI.
        Falls back to heuristic if LLM unavailable.
        """
        # Try AI-powered initial offer
        if self.llm.enabled:
            try:
                ai_offer = self._ai_initial_offer(product, inventory, posture)
                if ai_offer is not None:
                    logger.info("ai_initial_offer_used", offer=str(ai_offer))
                    return ai_offer
            except Exception as e:
                logger.error("ai_initial_offer_error", error=str(e))
        
        # Fallback to basic heuristic
        logger.info("initial_offer_fallback")
        return self._fallback_initial_offer(product, inventory, posture)
    
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
        Evaluate a buyer's offer using AI.
        
        The LLM makes the strategic decision.
        Hard constraints are enforced as post-LLM guardrails.
        Financial metrics are computed deterministically.
        """
        offered = buyer_offer.offered_price
        quantity = buyer_offer.offered_quantity or inventory.requested_quantity
        
        # Check hard constraints FIRST (before AI)
        violations = self._check_constraints(offered, product, posture)
        
        # Try AI-powered evaluation
        if self.llm.enabled:
            try:
                ai_decision = self._ai_evaluate_offer(
                    buyer_offer, product, inventory, strategy, posture, state, violations
                )
                if ai_decision is not None:
                    logger.info("ai_pricing_decision_used", decision=ai_decision.decision.value)
                    return ai_decision
            except Exception as e:
                logger.error("ai_pricing_evaluation_error", error=str(e))
        
        # Fallback to basic heuristic
        logger.info("pricing_evaluation_fallback")
        return self._fallback_evaluate(
            offered, quantity, product, posture, state, strategy, violations
        )
    
    # ==========================================================================
    # AI-Powered Methods
    # ==========================================================================
    
    def _ai_initial_offer(
        self,
        product: ProductData,
        inventory: InventoryContext,
        posture: StrategicPosture,
    ) -> Optional[Decimal]:
        """Use LLM to determine initial offer."""
        prompt = llm_prompts.build_initial_offer_pricing_prompt(
            product_name=product.product_name,
            base_price=str(product.base_price),
            cost_price=str(product.cost_price),
            min_acceptable_price=str(product.min_acceptable_price),
            target_price=str(posture.target_price),
            aggressiveness=str(posture.aggressiveness),
            mode="MAX_PROFIT" if posture.aggressiveness >= Decimal("0.5") else "MIN_LOSS",
            requested_quantity=inventory.requested_quantity,
            quantity_discount_factor=str(posture.quantity_discount_factor),
        )
        
        result = self.llm.generate_sync(
            system_prompt=llm_prompts.PRICING_STRATEGY_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3,
        )
        
        if not result.success:
            return None
        
        try:
            content = self._clean_json(result.content)
            data = json.loads(content)
            offer = Decimal(str(data["initial_offer"]))
            
            # Guardrails: clamp to valid range
            offer = max(product.min_acceptable_price, min(product.base_price, offer))
            
            # Apply quantity discount
            if inventory.requested_quantity > 1:
                offer = offer * posture.quantity_discount_factor
                offer = max(product.min_acceptable_price, offer)
            
            return self._round_price(offer)
        except (json.JSONDecodeError, KeyError, InvalidOperation, ValueError) as e:
            logger.warning("ai_initial_offer_parse_error", error=str(e))
            return None
    
    def _ai_evaluate_offer(
        self,
        buyer_offer: BuyerOffer,
        product: ProductData,
        inventory: InventoryContext,
        strategy: StrategicControls,
        posture: StrategicPosture,
        state: PricingState,
        violations: List[str],
    ) -> Optional[PricingDecision]:
        """Use LLM to evaluate buyer offer and make pricing decision."""
        offered = buyer_offer.offered_price
        quantity = buyer_offer.offered_quantity or inventory.requested_quantity
        
        prompt = llm_prompts.build_evaluate_offer_prompt(
            product_name=product.product_name,
            base_price=str(product.base_price),
            cost_price=str(product.cost_price),
            min_acceptable_price=str(product.min_acceptable_price),
            buyer_offered=str(offered),
            buyer_message=buyer_offer.message or "",
            current_round=state.current_round,
            max_rounds=strategy.max_rounds,
            our_last_offer=str(state.current_offer),
            buyer_last_offer=str(state.buyer_last_offer or "N/A"),
            target_price=str(posture.target_price),
            reservation_price=str(posture.reservation_price),
            walk_away_price=str(posture.walk_away_price),
            aggressiveness=str(posture.aggressiveness),
            flexibility=str(posture.flexibility),
            risk_tolerance=str(posture.risk_tolerance),
            mode=strategy.mode.value,
            concession_used=str(state.concession_used),
            total_concession_budget=str(posture.total_concession_budget),
            offers_history=", ".join(str(o) for o in state.offers_history),
            buyer_history=", ".join(str(o) for o in state.buyer_history),
            requested_quantity=quantity,
        )
        
        result = self.llm.generate_sync(
            system_prompt=llm_prompts.PRICING_STRATEGY_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3,
        )
        
        if not result.success:
            return None
        
        try:
            content = self._clean_json(result.content)
            data = json.loads(content)
            
            decision_str = data.get("decision", "counter").lower().strip()
            counter_price_raw = data.get("counter_price")
            
            # Map to enum
            if decision_str == "accept":
                decision = OfferDecision.ACCEPT
            elif decision_str == "reject":
                decision = OfferDecision.REJECT
            else:
                decision = OfferDecision.COUNTER
            
            # =====================================================
            # HARD GUARDRAILS — Override AI if it violates safety
            # =====================================================
            
            # GUARDRAIL 1: Cannot accept below walk_away_price
            if decision == OfferDecision.ACCEPT and offered < posture.walk_away_price:
                logger.warning("ai_guardrail_accept_below_walkaway",
                             offered=str(offered), walkaway=str(posture.walk_away_price))
                if state.current_round >= strategy.max_rounds:
                    decision = OfferDecision.REJECT
                else:
                    decision = OfferDecision.COUNTER
                    counter_price_raw = str(posture.reservation_price)
            
            # GUARDRAIL 2: Cannot accept below min_acceptable_price
            if decision == OfferDecision.ACCEPT and offered < product.min_acceptable_price:
                logger.warning("ai_guardrail_accept_below_min",
                             offered=str(offered), min_price=str(product.min_acceptable_price))
                decision = OfferDecision.COUNTER
                counter_price_raw = str(posture.reservation_price)
            
            # GUARDRAIL 3: Counter price must be >= reservation_price
            counter_price = None
            if decision == OfferDecision.COUNTER:
                if counter_price_raw is not None:
                    counter_price = Decimal(str(counter_price_raw))
                    counter_price = max(counter_price, posture.reservation_price)
                    counter_price = max(counter_price, product.min_acceptable_price)
                    counter_price = self._round_price(counter_price)
                else:
                    counter_price = self._round_price(posture.reservation_price)
            
            # GUARDRAIL 4: If out of rounds and not accepting, must reject or accept
            if state.current_round >= strategy.max_rounds and decision == OfferDecision.COUNTER:
                if offered >= posture.reservation_price:
                    decision = OfferDecision.ACCEPT
                    counter_price = None
                else:
                    decision = OfferDecision.REJECT
                    counter_price = None
            
            # Build the PricingDecision with deterministic metrics
            return self._build_decision(
                decision=decision,
                counter_price=counter_price,
                offered=offered,
                product=product,
                posture=posture,
                state=state,
                quantity=quantity,
                violations=violations,
            )
        except (json.JSONDecodeError, KeyError, InvalidOperation, ValueError) as e:
            logger.warning("ai_evaluate_offer_parse_error", error=str(e), content=result.content[:200])
            return None
    
    # ==========================================================================
    # Decision Builder (Deterministic Metrics)
    # ==========================================================================
    
    def _build_decision(
        self,
        decision: OfferDecision,
        counter_price: Optional[Decimal],
        offered: Decimal,
        product: ProductData,
        posture: StrategicPosture,
        state: PricingState,
        quantity: int,
        violations: List[str],
    ) -> PricingDecision:
        """Build PricingDecision with deterministic financial metrics."""
        margin_pct, profit_unit, total_profit = self._compute_metrics(
            offered, product.cost_price, quantity
        )
        
        # Track concession
        concession_made = Decimal("0")
        if decision == OfferDecision.COUNTER and counter_price and counter_price < state.current_offer:
            concession_made = state.current_offer - counter_price
        
        remaining_budget = posture.total_concession_budget - state.concession_used - concession_made
        remaining_budget = max(Decimal("0"), remaining_budget)
        
        budget_used_pct = Decimal("0")
        if posture.total_concession_budget > 0:
            budget_used_pct = ((state.concession_used + concession_made) / posture.total_concession_budget * 100)
        budget_used_pct = min(Decimal("100"), budget_used_pct)
        
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
            remaining_concession_budget=remaining_budget,
            concession_percentage_used=self._round_price(budget_used_pct),
        )
    
    # ==========================================================================
    # Constraint Checking (Hard Safety Layer)
    # ==========================================================================
    
    def _check_constraints(
        self,
        offered: Decimal,
        product: ProductData,
        posture: StrategicPosture,
    ) -> List[str]:
        """Check hard constraints. Returns list of violations."""
        violations = []
        
        if offered < posture.walk_away_price:
            violations.append(f"below_walk_away: {offered} < {posture.walk_away_price}")
        
        if offered < product.min_acceptable_price:
            violations.append(f"below_min_acceptable: {offered} < {product.min_acceptable_price}")
        
        if offered < product.cost_price:
            violations.append(f"below_cost: {offered} < {product.cost_price}")
        
        return violations
    
    # ==========================================================================
    # Fallback Heuristics (if LLM unavailable)
    # ==========================================================================
    
    def _fallback_initial_offer(
        self,
        product: ProductData,
        inventory: InventoryContext,
        posture: StrategicPosture,
    ) -> Decimal:
        """Basic heuristic for initial offer."""
        base = product.base_price
        target = posture.target_price
        
        if posture.aggressiveness >= Decimal("0.7"):
            initial = base
        elif posture.aggressiveness >= Decimal("0.4"):
            initial = target + (base - target) * Decimal("0.3")
        else:
            initial = target
        
        if inventory.requested_quantity > 1:
            initial = initial * posture.quantity_discount_factor
        
        return self._round_price(initial)
    
    def _fallback_evaluate(
        self,
        offered: Decimal,
        quantity: int,
        product: ProductData,
        posture: StrategicPosture,
        state: PricingState,
        strategy: StrategicControls,
        violations: List[str],
    ) -> PricingDecision:
        """Basic heuristic evaluation when LLM is unavailable."""
        # If constraint violations exist
        if violations:
            if state.current_round >= strategy.max_rounds:
                return self._build_decision(
                    OfferDecision.REJECT, None, offered, product, posture, state, quantity, violations
                )
            return self._build_decision(
                OfferDecision.COUNTER, self._round_price(posture.reservation_price),
                offered, product, posture, state, quantity, violations
            )
        
        target = posture.target_price
        reservation = posture.reservation_price
        
        # Accept if at or above target
        if offered >= target:
            return self._build_decision(
                OfferDecision.ACCEPT, None, offered, product, posture, state, quantity, violations
            )
        
        # Accept if at/above reservation in late rounds or MIN_LOSS
        if offered >= reservation:
            if state.current_round >= strategy.max_rounds - 1:
                return self._build_decision(
                    OfferDecision.ACCEPT, None, offered, product, posture, state, quantity, violations
                )
            if strategy.mode == NegotiationMode.MIN_LOSS:
                return self._build_decision(
                    OfferDecision.ACCEPT, None, offered, product, posture, state, quantity, violations
                )
        
        # Counter — compute concession
        remaining_budget = posture.total_concession_budget - state.concession_used
        if remaining_budget <= 0:
            counter = state.current_offer
        else:
            concession = posture.per_round_concession
            # Adjust for buyer movement
            if state.buyer_last_offer is not None:
                buyer_movement = offered - state.buyer_last_offer
                if buyer_movement <= 0:
                    concession *= Decimal("0.3")
                elif buyer_movement < concession:
                    concession = buyer_movement * Decimal("0.8")
            counter = max(state.current_offer - concession, reservation)
        
        # Out of rounds — accept at reservation or reject
        if state.current_round >= strategy.max_rounds:
            if offered >= reservation:
                return self._build_decision(
                    OfferDecision.ACCEPT, None, offered, product, posture, state, quantity, violations
                )
            return self._build_decision(
                OfferDecision.REJECT, None, offered, product, posture, state, quantity, violations
            )
        
        return self._build_decision(
            OfferDecision.COUNTER, self._round_price(counter),
            offered, product, posture, state, quantity, violations
        )
    
    # ==========================================================================
    # Utility Methods
    # ==========================================================================
    
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
    
    def _clean_json(self, content: str) -> str:
        """Clean LLM response to extract JSON."""
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        return content
