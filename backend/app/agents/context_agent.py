"""
Context Analysis Agent — AI-Powered

Purpose: Interpret seller inputs into strategic posture using LLM reasoning.
This agent performs NO negotiation - only analysis.

Architecture:
1. Send product/inventory/strategy data to LLM
2. LLM reasons about optimal strategy and returns structured JSON
3. Parse and validate the response
4. Clamp all values to safe ranges
5. If LLM fails → fall back to basic heuristic calculation

Outputs:
- Aggressiveness score (0-1)
- Concession budget
- Preferred closing round
- Risk tolerance level
"""
import json
import structlog
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from typing import Tuple, Optional

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
from ..infrastructure.llm.openai_client import get_llm_client, OpenRouterClient
from ..infrastructure.llm import prompt_templates as llm_prompts

logger = structlog.get_logger(__name__)


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
    AI-powered context analysis agent.
    
    Uses LLM to reason about optimal negotiation strategy based on
    seller inputs. Falls back to basic heuristics if LLM is unavailable.
    """
    
    def __init__(self, llm_client: Optional[OpenRouterClient] = None):
        self.llm = llm_client or get_llm_client()
    
    def analyze(
        self,
        product: ProductData,
        inventory: InventoryContext,
        strategy: StrategicControls,
    ) -> StrategicPosture:
        """
        Analyze inputs and produce strategic posture using AI.
        
        This is the main entry point for context analysis.
        """
        # Try AI-powered analysis first
        if self.llm.enabled:
            try:
                posture = self._ai_analyze(product, inventory, strategy)
                if posture is not None:
                    logger.info("ai_context_analysis_used", aggressiveness=str(posture.aggressiveness))
                    return posture
            except Exception as e:
                logger.error("ai_context_analysis_error", error=str(e))
        
        # Fallback to basic heuristic
        logger.info("context_analysis_fallback")
        return self._fallback_analyze(product, inventory, strategy)
    
    def _ai_analyze(
        self,
        product: ProductData,
        inventory: InventoryContext,
        strategy: StrategicControls,
    ) -> Optional[StrategicPosture]:
        """Use LLM to analyze context and produce strategic posture."""
        prompt = llm_prompts.build_context_analysis_prompt(
            product_name=product.product_name,
            base_price=str(product.base_price),
            cost_price=str(product.cost_price),
            min_acceptable_price=str(product.min_acceptable_price),
            max_loss_percentage=str(product.max_loss_percentage),
            available_quantity=inventory.available_quantity,
            requested_quantity=inventory.requested_quantity,
            inventory_pressure=inventory.inventory_pressure.value,
            sales_frequency=inventory.sales_frequency.value,
            mode=strategy.mode.value,
            urgency=strategy.urgency.value,
            relationship_priority=strategy.relationship_priority.value,
            max_rounds=strategy.max_rounds,
        )
        
        result = self.llm.generate_sync(
            system_prompt=llm_prompts.CONTEXT_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.4,  # Lower temp for more consistent analysis
        )
        
        if not result.success:
            logger.warning("ai_context_analysis_llm_failed", error=result.error)
            return None
        
        # Parse JSON response
        try:
            # Clean response - strip markdown code blocks if present
            content = result.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("ai_context_analysis_parse_error", error=str(e), content=result.content[:200])
            return None
        
        # Validate and build posture with guardrails
        try:
            return self._build_posture_from_ai(data, product, strategy)
        except Exception as e:
            logger.warning("ai_context_analysis_validation_error", error=str(e))
            return None
    
    def _build_posture_from_ai(
        self,
        data: dict,
        product: ProductData,
        strategy: StrategicControls,
    ) -> StrategicPosture:
        """Build and validate StrategicPosture from AI response with guardrails."""
        base = product.base_price
        cost = product.cost_price
        floor = product.min_acceptable_price
        
        # Clamp core metrics to [0.1, 1.0]
        aggressiveness = self._clamp_decimal(data.get("aggressiveness", 0.5), "0.1", "1.0")
        flexibility = self._clamp_decimal(data.get("flexibility", 0.5), "0.1", "1.0")
        risk_tolerance = self._clamp_decimal(data.get("risk_tolerance", 0.5), "0.1", "1.0")
        
        # Validate price targets with hard guardrails
        target_price = self._to_decimal(data.get("target_price", str(base)))
        reservation_price = self._to_decimal(data.get("reservation_price", str(floor)))
        walk_away_price = self._to_decimal(data.get("walk_away_price", str(floor)))
        
        # HARD GUARDRAILS — AI cannot violate these
        target_price = min(base, max(floor, target_price))
        # reservation_price = min_acceptable_price (the real acceptance floor)
        reservation_price = floor
        
        # Walk-away: allow below cost only if max_loss_percentage > 0
        if strategy.mode == NegotiationMode.MIN_LOSS and product.max_loss_percentage > 0:
            max_loss = cost * (product.max_loss_percentage / Decimal("100"))
            absolute_floor = cost - max_loss
        else:
            absolute_floor = floor
        
        walk_away_price = min(reservation_price, max(absolute_floor, walk_away_price))
        
        # Ensure hierarchy: target >= reservation >= walk_away
        target_price = max(target_price, reservation_price)
        reservation_price = max(reservation_price, walk_away_price)
        
        # Concession budget
        total_concession_budget = target_price - reservation_price
        
        # Per-round concession
        ai_per_round = self._to_decimal(data.get("per_round_concession", "0"))
        max_per_round = total_concession_budget / Decimal(str(max(1, strategy.max_rounds)))
        per_round_concession = min(ai_per_round, max_per_round * Decimal("2")) if ai_per_round > 0 else max_per_round
        
        # Preferred closing round
        preferred_closing_round = int(data.get("preferred_closing_round", 3))
        preferred_closing_round = max(1, min(preferred_closing_round, strategy.max_rounds))
        
        # Quantity discount factor
        quantity_discount_factor = self._clamp_decimal(
            data.get("quantity_discount_factor", 1.0), "0.85", "1.0"
        )
        
        return StrategicPosture(
            aggressiveness=aggressiveness,
            flexibility=flexibility,
            risk_tolerance=risk_tolerance,
            target_price=self._round_price(target_price),
            reservation_price=self._round_price(reservation_price),
            walk_away_price=self._round_price(walk_away_price),
            total_concession_budget=self._round_price(total_concession_budget),
            per_round_concession=self._round_price(per_round_concession),
            preferred_closing_round=preferred_closing_round,
            quantity_discount_factor=quantity_discount_factor,
        )
    
    # ==========================================================================
    # Fallback Heuristic (if LLM unavailable)
    # ==========================================================================
    
    def _fallback_analyze(
        self,
        product: ProductData,
        inventory: InventoryContext,
        strategy: StrategicControls,
    ) -> StrategicPosture:
        """Basic heuristic fallback when LLM is unavailable."""
        base = product.base_price
        cost = product.cost_price
        floor = product.min_acceptable_price
        
        # Simple aggressiveness based on mode
        if strategy.mode == NegotiationMode.MAX_PROFIT:
            aggressiveness = Decimal("0.75")
            flexibility = Decimal("0.3")
            risk_tolerance = Decimal("0.7")
        else:
            aggressiveness = Decimal("0.4")
            flexibility = Decimal("0.7")
            risk_tolerance = Decimal("0.3")
        
        # Urgency adjustments
        if strategy.urgency == UrgencyLevel.HIGH:
            aggressiveness -= Decimal("0.15")
            risk_tolerance -= Decimal("0.2")
        elif strategy.urgency == UrgencyLevel.LOW:
            aggressiveness += Decimal("0.1")
        
        # Inventory pressure adjustments
        if inventory.inventory_pressure == PressureLevel.HIGH:
            aggressiveness -= Decimal("0.15")
            risk_tolerance -= Decimal("0.2")
        
        aggressiveness = max(Decimal("0.1"), min(Decimal("1.0"), aggressiveness))
        flexibility = max(Decimal("0.1"), min(Decimal("1.0"), flexibility))
        risk_tolerance = max(Decimal("0.1"), min(Decimal("1.0"), risk_tolerance))
        
        # Price targets
        margin = base - cost
        target_discount = margin * (Decimal("1.0") - aggressiveness) * Decimal("0.3")
        target_price = base - target_discount
        
        # reservation_price = min_acceptable_price (the real acceptance floor)
        reservation_price = floor
        
        if strategy.mode == NegotiationMode.MIN_LOSS and product.max_loss_percentage > 0:
            max_loss = cost * (product.max_loss_percentage / Decimal("100"))
            walk_away_price = cost - max_loss
        else:
            walk_away_price = floor
        
        target_price = max(target_price, reservation_price)
        reservation_price = max(reservation_price, walk_away_price)
        
        concession_budget = target_price - reservation_price
        per_round = concession_budget / Decimal(str(max(1, strategy.max_rounds)))
        
        preferred_round = min(3, strategy.max_rounds) if strategy.mode == NegotiationMode.MAX_PROFIT else min(2, strategy.max_rounds)
        
        # Quantity discount
        ratio = Decimal(str(inventory.requested_quantity)) / Decimal(str(inventory.available_quantity))
        if ratio >= Decimal("0.5"):
            qty_discount = Decimal("0.95")
        elif ratio >= Decimal("0.25"):
            qty_discount = Decimal("0.97")
        else:
            qty_discount = Decimal("1.0")
        
        return StrategicPosture(
            aggressiveness=aggressiveness,
            flexibility=flexibility,
            risk_tolerance=risk_tolerance,
            target_price=self._round_price(target_price),
            reservation_price=self._round_price(reservation_price),
            walk_away_price=self._round_price(walk_away_price),
            total_concession_budget=self._round_price(concession_budget),
            per_round_concession=self._round_price(per_round),
            preferred_closing_round=preferred_round,
            quantity_discount_factor=qty_discount,
        )
    
    # ==========================================================================
    # Utility Methods
    # ==========================================================================
    
    def _to_decimal(self, value, default: str = "0") -> Decimal:
        """Safely convert value to Decimal."""
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal(default)
    
    def _clamp_decimal(self, value, low: str, high: str) -> Decimal:
        """Convert to Decimal and clamp to range."""
        d = self._to_decimal(value, low)
        return max(Decimal(low), min(Decimal(high), d))
    
    def _round_price(self, price: Decimal) -> Decimal:
        """Round price to 2 decimal places."""
        from decimal import ROUND_HALF_UP
        return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
