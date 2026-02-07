"""
Pricing Strategy Agent — AI-Powered

Purpose: Make pricing decisions using LLM intelligence + hard safety guardrails.

CORE RULES (enforced as guardrails, AI cannot override):
1. Accept only if buyer's offer is within ±$3 of our current counter (rounds 1-4)
   After round 5, threshold widens progressively (+$5/round) — never below cost_price
2. Counter price must NEVER go UP from our previous counter
3. Counter price must NEVER go below min_acceptable_price
4. If buyer offers far below our counter → COUNTER or REJECT (never accept)
5. Financial metrics (margin, profit) are always computed deterministically

Architecture:
    LLM decides → Guardrails enforce → Metrics computed → Response built
    If LLM fails → Fallback heuristic with same guardrails
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
    current_offer: Decimal          # Our last offer to the buyer
    buyer_last_offer: Optional[Decimal]
    concession_used: Decimal        # Total $ conceded so far
    offers_history: List[Decimal]   # All our offers (chronological)
    buyer_history: List[Decimal]    # All buyer offers (chronological)

    def __post_init__(self):
        if not isinstance(self.concession_used, Decimal):
            self.concession_used = Decimal(str(self.concession_used))


class PricingStrategyAgent:
    """
    AI-powered pricing engine with hard safety guardrails.

    The LLM handles strategy (how much to concede, when to push back).
    Guardrails handle safety (never accept below floor, never counter up).
    """

    def __init__(self, llm_client: Optional[OpenRouterClient] = None):
        self.llm = llm_client or get_llm_client()

    # ══════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════════

    def compute_initial_offer(
        self,
        product: ProductData,
        inventory: InventoryContext,
        posture: StrategicPosture,
    ) -> Decimal:
        """Compute the seller's opening offer."""

        # Try AI
        if self.llm.enabled:
            try:
                ai_offer = self._ai_initial_offer(product, inventory, posture)
                if ai_offer is not None:
                    logger.info("ai_initial_offer", price=str(ai_offer))
                    return ai_offer
            except Exception as e:
                logger.error("ai_initial_offer_error", error=str(e))

        # Fallback
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
        """Evaluate buyer's offer → accept / counter / reject."""

        offered = buyer_offer.offered_price
        quantity = buyer_offer.offered_quantity or inventory.requested_quantity

        # ─── DYNAMIC ACCEPTANCE: proximity to our current counter ────────
        # Rounds 1-4: accept only if buyer is within $3 of our counter
        # Rounds 5+:  threshold widens progressively (buyer wore us down)
        round_num = state.current_round
        if round_num <= 4:
            acceptance_threshold = Decimal("3")
        else:
            # Widens by $5 per round after round 4
            acceptance_threshold = Decimal("3") + Decimal(str(round_num - 4)) * Decimal("5")

        # Accept if buyer's offer is close enough to our counter AND above cost
        if offered >= (state.current_offer - acceptance_threshold) and offered >= product.cost_price:
            logger.info(
                "proximity_accept",
                offered=str(offered),
                our_counter=str(state.current_offer),
                threshold=str(acceptance_threshold),
                round=round_num,
            )
            return self._build_decision(
                decision=OfferDecision.ACCEPT,
                counter_price=None,
                offered=offered,
                product=product,
                posture=posture,
                state=state,
                quantity=quantity,
                violations=[],
            )

        # ─── Below min_acceptable: check how bad it is ───────────────────
        violations = self._check_constraints(offered, product, posture)

        # Try AI to decide counter strategy
        if self.llm.enabled:
            try:
                ai_decision = self._ai_evaluate_offer(
                    buyer_offer, product, inventory, strategy,
                    posture, state, violations,
                )
                if ai_decision is not None:
                    logger.info("ai_pricing_decision", decision=ai_decision.decision.value)
                    return ai_decision
            except Exception as e:
                logger.error("ai_pricing_error", error=str(e))

        # Fallback heuristic
        return self._fallback_evaluate(
            offered, quantity, product, posture, state, strategy, violations
        )

    # ══════════════════════════════════════════════════════════════════════
    # AI METHODS
    # ══════════════════════════════════════════════════════════════════════

    def _ai_initial_offer(
        self,
        product: ProductData,
        inventory: InventoryContext,
        posture: StrategicPosture,
    ) -> Optional[Decimal]:
        """LLM picks the opening price."""

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
            data = json.loads(self._clean_json(result.content))
            offer = Decimal(str(data["initial_offer"]))

            # Guardrail: clamp between min_acceptable and base
            offer = max(product.min_acceptable_price, min(product.base_price, offer))

            # Quantity discount
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
        """LLM decides counter/reject for offers below min_acceptable."""

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
            data = json.loads(self._clean_json(result.content))
            decision_str = data.get("decision", "counter").lower().strip()
            counter_price_raw = data.get("counter_price")

            if decision_str == "reject":
                decision = OfferDecision.REJECT
            else:
                decision = OfferDecision.COUNTER   # default to counter

            # NOTE: Acceptance is handled by proximity check in evaluate_offer().
            # If AI says "accept" here, override to COUNTER — only the
            # proximity threshold decides acceptance.
            if decision_str == "accept":
                decision = OfferDecision.COUNTER
                counter_price_raw = counter_price_raw or str(state.current_offer)

            # ── Guardrails for COUNTER ────────────────────────────────
            counter_price = None
            if decision == OfferDecision.COUNTER:
                if counter_price_raw is not None:
                    counter_price = Decimal(str(counter_price_raw))
                else:
                    counter_price = state.current_offer

                # RULE 2: Counter must NEVER go UP
                counter_price = min(counter_price, state.current_offer)

                # RULE 3: Counter must NEVER go below min_acceptable
                counter_price = max(counter_price, product.min_acceptable_price)

                counter_price = self._round_price(counter_price)

            # Last round: can't counter, must reject
            if state.current_round >= strategy.max_rounds and decision == OfferDecision.COUNTER:
                decision = OfferDecision.REJECT
                counter_price = None

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
            logger.warning("ai_evaluate_parse_error", error=str(e),
                           content=result.content[:200])
            return None

    # ══════════════════════════════════════════════════════════════════════
    # FALLBACK HEURISTICS (when LLM is unavailable)
    # ══════════════════════════════════════════════════════════════════════

    def _fallback_initial_offer(
        self,
        product: ProductData,
        inventory: InventoryContext,
        posture: StrategicPosture,
    ) -> Decimal:
        """Simple heuristic opening offer."""
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

        return self._round_price(max(initial, product.min_acceptable_price))

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
        """Heuristic for offers below min_acceptable (LLM unavailable)."""

        # Last round: reject (buyer hasn't met our minimum)
        if state.current_round >= strategy.max_rounds:
            return self._build_decision(
                OfferDecision.REJECT, None, offered,
                product, posture, state, quantity, violations,
            )

        # Compute a concession from our last offer
        remaining_budget = posture.total_concession_budget - state.concession_used
        if remaining_budget <= 0:
            counter = state.current_offer
        else:
            concession = posture.per_round_concession
            # If buyer didn't move up, concede less
            if state.buyer_last_offer is not None:
                buyer_movement = offered - state.buyer_last_offer
                if buyer_movement <= 0:
                    concession *= Decimal("0.3")
                elif buyer_movement < concession:
                    concession = buyer_movement * Decimal("0.8")
            counter = state.current_offer - concession

        # RULE 2: Counter must NEVER go UP
        counter = min(counter, state.current_offer)

        # RULE 3: Counter must NEVER go below min_acceptable
        counter = max(counter, product.min_acceptable_price)

        return self._build_decision(
            OfferDecision.COUNTER, self._round_price(counter),
            offered, product, posture, state, quantity, violations,
        )

    # ══════════════════════════════════════════════════════════════════════
    # DECISION BUILDER
    # ══════════════════════════════════════════════════════════════════════

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

        concession_made = Decimal("0")
        if decision == OfferDecision.COUNTER and counter_price and counter_price < state.current_offer:
            concession_made = state.current_offer - counter_price

        remaining_budget = max(
            Decimal("0"),
            posture.total_concession_budget - state.concession_used - concession_made,
        )

        budget_used_pct = Decimal("0")
        if posture.total_concession_budget > 0:
            budget_used_pct = (
                (state.concession_used + concession_made)
                / posture.total_concession_budget
                * 100
            )
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

    # ══════════════════════════════════════════════════════════════════════
    # CONSTRAINT CHECK
    # ══════════════════════════════════════════════════════════════════════

    def _check_constraints(
        self,
        offered: Decimal,
        product: ProductData,
        posture: StrategicPosture,
    ) -> List[str]:
        """Check hard constraints. Returns list of violation descriptions."""
        violations = []
        if offered < product.min_acceptable_price:
            violations.append(
                f"below_min_acceptable: {offered} < {product.min_acceptable_price}"
            )
        if offered < product.cost_price:
            violations.append(f"below_cost: {offered} < {product.cost_price}")
        if offered < posture.walk_away_price:
            violations.append(
                f"below_walk_away: {offered} < {posture.walk_away_price}"
            )
        return violations

    # ══════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ══════════════════════════════════════════════════════════════════════

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
        return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _clean_json(self, content: str) -> str:
        """Strip markdown fences from LLM JSON response."""
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        return content
