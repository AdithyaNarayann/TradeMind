"""
Conversation Agent

Purpose: Convert pricing decisions into natural language.
This agent NEVER makes numeric decisions - only explains them.

Rules:
- Never invent numbers
- Never contradict pricing agent
- Only explain, justify, or soften decisions
- Uses LLM (OpenRouter) for natural language when available
- Falls back to templates if LLM fails or is not configured
- ALL LLM output is validated before returning
"""
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass
import structlog

from ..models import (
    OfferDecision,
    NegotiationMode,
    NegotiationStatus,
    PricingDecision,
)
from ..infrastructure.llm.openai_client import get_llm_client, OpenRouterClient
from ..services.llm_validator import get_validator, LLMValidator
from ..infrastructure.llm import prompt_templates as llm_prompts

logger = structlog.get_logger(__name__)


@dataclass
class ConversationContext:
    """Context needed to generate conversation."""
    round_number: int
    max_rounds: int
    mode: NegotiationMode
    product_name: str
    quantity: int
    buyer_offered: Optional[Decimal]
    our_offer: Optional[Decimal]


class ConversationAgent:
    """
    Generates natural language responses for negotiation turns.
    
    Architecture:
    1. Try LLM (OpenRouter) for natural, context-aware responses
    2. Validate LLM output against pricing decision
    3. If validation fails OR LLM unavailable → fall back to templates
    
    The LLM NEVER decides prices. It only communicates them.
    """
    
    def __init__(
        self,
        llm_client: Optional[OpenRouterClient] = None,
        validator: Optional[LLMValidator] = None,
    ):
        self.llm = llm_client or get_llm_client()
        self.validator = validator or get_validator()
    
    # ==========================================================================
    # Template Collections (Fallback)
    # ==========================================================================
    
    INITIAL_OFFER_TEMPLATES = {
        NegotiationMode.MAX_PROFIT: [
            "Thank you for your interest in {product}. Based on our current pricing, I can offer {quantity} unit(s) at ${offer} per unit.",
            "I appreciate you reaching out about {product}. Our best price for {quantity} unit(s) is ${offer} each.",
        ],
        NegotiationMode.MIN_LOSS: [
            "Thank you for considering {product}. I can offer {quantity} unit(s) at ${offer} per unit to close this quickly.",
            "I'm motivated to make this deal work. For {quantity} unit(s) of {product}, I'm offering ${offer} each.",
        ],
    }
    
    ACCEPT_TEMPLATES = [
        "I accept your offer of ${price} per unit for {quantity} unit(s). Deal confirmed.",
        "We have a deal at ${price} per unit. Thank you for the negotiation.",
        "Agreed! ${price} per unit for {quantity} unit(s) works for us.",
    ]
    
    COUNTER_TEMPLATES = {
        NegotiationMode.MAX_PROFIT: {
            "early": [
                "I appreciate the offer of ${buyer_offer}, but I need ${our_offer} per unit to make this work.",
                "That's a bit lower than I can go. I can do ${our_offer} per unit.",
                "I understand your position. My best offer is ${our_offer} per unit.",
            ],
            "mid": [
                "We're getting closer. I can meet you at ${our_offer} per unit.",
                "I've reviewed the numbers and can offer ${our_offer} per unit.",
            ],
            "late": [
                "This is my final offer: ${our_offer} per unit. I can't go lower.",
                "I'm at ${our_offer} per unit. This is as far as I can stretch.",
            ],
        },
        NegotiationMode.MIN_LOSS: {
            "early": [
                "I hear you at ${buyer_offer}. Let me offer ${our_offer} per unit.",
                "I want to make this work. How about ${our_offer} per unit?",
            ],
            "mid": [
                "I'm coming down to ${our_offer} per unit. That's a significant move.",
                "Let's close this at ${our_offer} per unit.",
            ],
            "late": [
                "To close this now, I can do ${our_offer} per unit. Final offer.",
                "${our_offer} per unit is my bottom line. Let's shake on it.",
            ],
        },
    }
    
    REJECT_TEMPLATES = [
        "I'm sorry, but I can't go below my minimum. Thank you for your time.",
        "Unfortunately, we couldn't reach an agreement. Perhaps another time.",
        "The numbers don't work at that price. I'll have to pass on this deal.",
    ]
    
    CONSTRAINT_VIOLATION_TEMPLATES = [
        "That offer is quite a bit lower than where I can go. Let's work together to find a price that makes sense for both of us.",
        "I appreciate the offer, but {product} has premium quality that commands a fair price. What's the best you can do?",
        "I understand you're looking for value, but I can't go that low. How about we meet somewhere in the middle?",
    ]
    
    SESSION_EXPIRED_TEMPLATES = [
        "We've reached the end of our negotiation window without agreement.",
        "Our negotiation has concluded without a deal. Thank you for your time.",
    ]
    
    # ==========================================================================
    # Public Methods — LLM-first with template fallback
    # ==========================================================================
    
    def generate_initial_message(
        self,
        offer: Decimal,
        context: ConversationContext,
    ) -> str:
        """Generate the opening offer message."""
        # Try LLM first
        if self.llm.enabled:
            llm_result = self.llm.generate_sync(
                system_prompt=llm_prompts.SYSTEM_PROMPT,
                user_prompt=llm_prompts.build_initial_offer_prompt(
                    product_name=context.product_name,
                    quantity=context.quantity,
                    offer_price=self._format_price(offer),
                    mode=context.mode.value,
                ),
                temperature=0.7,
            )
            
            if llm_result.success:
                # Build a minimal decision for validation
                from ..models import PricingDecision, OfferDecision
                mock_decision = PricingDecision(
                    decision=OfferDecision.COUNTER,
                    counter_offer_price=offer,
                    margin_percentage=Decimal("0"),
                    profit_per_unit=Decimal("0"),
                    total_profit=Decimal("0"),
                    within_constraints=True,
                    remaining_concession_budget=Decimal("0"),
                    concession_percentage_used=Decimal("0"),
                )
                
                validation = self.validator.validate(
                    llm_output=llm_result.content,
                    decision=mock_decision,
                    expected_price=offer,
                )
                
                if validation.is_valid:
                    logger.info("llm_used", action="initial_offer", model=llm_result.model)
                    return validation.cleaned_content
                else:
                    logger.warning(
                        "llm_validation_failed",
                        action="initial_offer",
                        violations=validation.violations,
                    )
        
        # Fallback to template
        logger.info("template_fallback", action="initial_offer")
        return self._template_initial(offer, context)
    
    def generate_response(
        self,
        decision: PricingDecision,
        context: ConversationContext,
        floor_price: Optional[Decimal] = None,
    ) -> str:
        """Generate response message based on pricing decision."""
        # Try LLM first
        if self.llm.enabled:
            llm_message = self._try_llm_response(decision, context, floor_price)
            if llm_message is not None:
                return llm_message
        
        # Fallback to templates
        logger.info("template_fallback", action=decision.decision.value)
        return self._template_response(decision, context, floor_price)
    
    def generate_session_expired(self, context: ConversationContext) -> str:
        """Generate message for expired session."""
        if self.llm.enabled:
            llm_result = self.llm.generate_sync(
                system_prompt=llm_prompts.SYSTEM_PROMPT,
                user_prompt=llm_prompts.build_session_expired_prompt(
                    product_name=context.product_name,
                    round_number=context.round_number,
                    max_rounds=context.max_rounds,
                ),
                temperature=0.7,
            )
            if llm_result.success and len(llm_result.content) > 10:
                logger.info("llm_used", action="session_expired", model=llm_result.model)
                return llm_result.content
        
        return self.SESSION_EXPIRED_TEMPLATES[0]
    
    def generate_buyer_walked(self, context: ConversationContext) -> str:
        """Generate message when buyer ends negotiation."""
        return "I understand. Thank you for your time. Feel free to reach out if you reconsider."
    
    # ==========================================================================
    # LLM Response Generation (with validation)
    # ==========================================================================
    
    def _try_llm_response(
        self,
        decision: PricingDecision,
        context: ConversationContext,
        floor_price: Optional[Decimal],
    ) -> Optional[str]:
        """
        Try to generate an LLM response with validation.
        Returns None if LLM fails or validation fails.
        """
        try:
            if decision.decision == OfferDecision.ACCEPT:
                prompt = llm_prompts.build_accept_prompt(
                    product_name=context.product_name,
                    quantity=context.quantity,
                    accepted_price=self._format_price(decision.accepted_price),
                    round_number=context.round_number,
                    max_rounds=context.max_rounds,
                )
                expected_price = decision.accepted_price
                
            elif decision.decision == OfferDecision.REJECT:
                prompt = llm_prompts.build_reject_prompt(
                    product_name=context.product_name,
                    quantity=context.quantity,
                    buyer_offered=self._format_price(context.buyer_offered),
                    round_number=context.round_number,
                    max_rounds=context.max_rounds,
                )
                expected_price = None
                
            elif decision.decision == OfferDecision.COUNTER:
                prompt = llm_prompts.build_counter_prompt(
                    product_name=context.product_name,
                    quantity=context.quantity,
                    buyer_offered=self._format_price(context.buyer_offered),
                    our_counter=self._format_price(decision.counter_offer_price),
                    round_number=context.round_number,
                    max_rounds=context.max_rounds,
                    mode=context.mode.value,
                    concession_pct_used=self._format_price(decision.concession_percentage_used),
                    is_constraint_violation=not decision.within_constraints,
                )
                expected_price = decision.counter_offer_price
            else:
                return None
            
            # Call LLM
            llm_result = self.llm.generate_sync(
                system_prompt=llm_prompts.SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.7,
            )
            
            if not llm_result.success:
                logger.warning("llm_failed", action=decision.decision.value, error=llm_result.error)
                return None
            
            # Validate
            validation = self.validator.validate(
                llm_output=llm_result.content,
                decision=decision,
                expected_price=expected_price,
                buyer_offered=context.buyer_offered,
            )
            
            if validation.is_valid:
                logger.info(
                    "llm_used",
                    action=decision.decision.value,
                    model=llm_result.model,
                    tokens=llm_result.tokens_used,
                )
                return validation.cleaned_content
            else:
                logger.warning(
                    "llm_validation_failed",
                    action=decision.decision.value,
                    violations=validation.violations,
                    content_preview=llm_result.content[:100],
                )
                return None
        
        except Exception as e:
            logger.error("llm_response_error", error=str(e))
            return None
    
    # ==========================================================================
    # Template Fallback Methods
    # ==========================================================================
    
    def _template_initial(self, offer: Decimal, context: ConversationContext) -> str:
        """Template fallback for initial offer."""
        templates = self.INITIAL_OFFER_TEMPLATES[context.mode]
        template = templates[0]
        return template.format(
            product=context.product_name,
            quantity=context.quantity,
            offer=self._format_price(offer),
        )
    
    def _template_response(
        self,
        decision: PricingDecision,
        context: ConversationContext,
        floor_price: Optional[Decimal] = None,
    ) -> str:
        """Template fallback for turn responses."""
        if decision.decision == OfferDecision.ACCEPT:
            return self._generate_accept(decision, context)
        elif decision.decision == OfferDecision.REJECT:
            return self._generate_reject(decision, context)
        elif decision.decision == OfferDecision.COUNTER:
            if not decision.within_constraints:
                return self._generate_constraint_violation(
                    decision, context, floor_price
                )
            return self._generate_counter(decision, context)
        return "Let me review that offer."
    
    def _generate_accept(
        self,
        decision: PricingDecision,
        context: ConversationContext,
    ) -> str:
        """Generate acceptance message."""
        template = self.ACCEPT_TEMPLATES[0]
        return template.format(
            price=self._format_price(decision.accepted_price),
            quantity=context.quantity,
        )
    
    def _generate_reject(
        self,
        decision: PricingDecision,
        context: ConversationContext,
    ) -> str:
        """Generate rejection message."""
        return self.REJECT_TEMPLATES[0]
    
    def _generate_counter(
        self,
        decision: PricingDecision,
        context: ConversationContext,
    ) -> str:
        """Generate counter-offer message."""
        phase = self._get_phase(context.round_number, context.max_rounds)
        templates = self.COUNTER_TEMPLATES[context.mode][phase]
        template = templates[0]
        
        return template.format(
            buyer_offer=self._format_price(context.buyer_offered),
            our_offer=self._format_price(decision.counter_offer_price),
            quantity=context.quantity,
            product=context.product_name,
        )
    
    def _generate_constraint_violation(
        self,
        decision: PricingDecision,
        context: ConversationContext,
        floor_price: Optional[Decimal],
    ) -> str:
        """Generate response for constraint violation — NEVER reveal floor price."""
        template = self.CONSTRAINT_VIOLATION_TEMPLATES[0]
        
        return template.format(
            buyer_offer=self._format_price(context.buyer_offered),
            product=context.product_name,
        )
    
    def _get_phase(self, current_round: int, max_rounds: int) -> str:
        """Determine negotiation phase."""
        progress = current_round / max_rounds
        
        if progress <= 0.33:
            return "early"
        elif progress <= 0.66:
            return "mid"
        else:
            return "late"
    
    def _format_price(self, price: Optional[Decimal]) -> str:
        """Format price for display."""
        if price is None:
            return "N/A"
        return f"{price:.2f}"
