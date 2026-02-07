"""
Conversation Agent

Purpose: Convert pricing decisions into natural language.
This agent NEVER makes numeric decisions - only explains them.

Rules:
- Never invent numbers
- Never contradict pricing agent
- Only explain, justify, or soften decisions
- Fallback to templates if needed
"""
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

from ..models import (
    OfferDecision,
    NegotiationMode,
    NegotiationStatus,
    PricingDecision,
)


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
    
    This agent is template-based by default, ensuring:
    - No hallucinated numbers
    - Consistent, predictable messaging
    - Full alignment with pricing decisions
    
    Can be extended with LLM for more natural responses,
    but LLM output must be validated against pricing decision.
    """
    
    # ==========================================================================
    # Template Collections
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
        "That offer is below what I can consider. My minimum is ${floor}.",
        "I appreciate the offer, but ${buyer_offer} doesn't meet my constraints. I need at least ${floor}.",
        "That's outside my acceptable range. The lowest I can go is ${floor}.",
    ]
    
    SESSION_EXPIRED_TEMPLATES = [
        "We've reached the end of our negotiation window without agreement.",
        "Our negotiation has concluded without a deal. Thank you for your time.",
    ]
    
    # ==========================================================================
    # Public Methods
    # ==========================================================================
    
    def generate_initial_message(
        self,
        offer: Decimal,
        context: ConversationContext,
    ) -> str:
        """Generate the opening offer message."""
        templates = self.INITIAL_OFFER_TEMPLATES[context.mode]
        template = templates[0]  # Could randomize
        
        return template.format(
            product=context.product_name,
            quantity=context.quantity,
            offer=self._format_price(offer),
        )
    
    def generate_response(
        self,
        decision: PricingDecision,
        context: ConversationContext,
        floor_price: Optional[Decimal] = None,
    ) -> str:
        """Generate response message based on pricing decision."""
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
        
        # Fallback
        return "Let me review that offer."
    
    def generate_session_expired(self, context: ConversationContext) -> str:
        """Generate message for expired session."""
        return self.SESSION_EXPIRED_TEMPLATES[0]
    
    def generate_buyer_walked(self, context: ConversationContext) -> str:
        """Generate message when buyer ends negotiation."""
        return "I understand. Thank you for your time. Feel free to reach out if you reconsider."
    
    # ==========================================================================
    # Private Methods
    # ==========================================================================
    
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
        """Generate response for constraint violation."""
        template = self.CONSTRAINT_VIOLATION_TEMPLATES[0]
        
        return template.format(
            buyer_offer=self._format_price(context.buyer_offered),
            floor=self._format_price(floor_price or decision.counter_offer_price),
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
