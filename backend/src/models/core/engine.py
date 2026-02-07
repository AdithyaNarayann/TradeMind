"""
Negotiation Engine - Orchestration Layer

This is the main entry point that coordinates:
1. Context Analysis Agent
2. Pricing Strategy Agent  
3. Conversation Agent

Responsibilities:
- Session lifecycle
- Agent coordination
- State persistence
- Termination conditions
"""
from decimal import Decimal
from uuid import UUID
from typing import Optional, Tuple
from datetime import datetime

from ..models import (
    ProductData,
    InventoryContext,
    StrategicControls,
    CreateSessionRequest,
    CreateSessionResponse,
    BuyerOffer,
    NegotiationTurnRequest,
    NegotiationTurnResponse,
    PricingDecision,
    NegotiationStatus,
    OfferDecision,
    SessionSummary,
    NegotiationAnalytics,
)
from ..agents import (
    ContextAnalysisAgent,
    PricingStrategyAgent,
    PricingState,
    ConversationAgent,
    ConversationContext,
)
from .session import SessionManager, NegotiationSession, get_session_manager


class NegotiationEngine:
    """
    Main orchestration layer for the negotiation system.
    
    This class:
    - Coordinates all agents
    - Manages session state
    - Enforces termination conditions
    - Produces auditable outputs
    """
    
    def __init__(self, session_manager: Optional[SessionManager] = None):
        self.session_manager = session_manager or get_session_manager()
        
        # Initialize agents
        self.context_agent = ContextAnalysisAgent()
        self.pricing_agent = PricingStrategyAgent()
        self.conversation_agent = ConversationAgent()
    
    # ==========================================================================
    # Public API
    # ==========================================================================
    
    def create_session(
        self,
        request: CreateSessionRequest,
        client_ip: Optional[str] = None,
    ) -> CreateSessionResponse:
        """
        Create a new negotiation session.
        
        This:
        1. Validates all inputs
        2. Computes strategic posture
        3. Generates initial offer
        4. Creates session state
        """
        # Step 1: Analyze context to get strategic posture
        posture = self.context_agent.analyze(
            product=request.product,
            inventory=request.inventory,
            strategy=request.strategy,
        )
        
        # Step 2: Compute initial offer
        initial_offer = self.pricing_agent.compute_initial_offer(
            product=request.product,
            inventory=request.inventory,
            posture=posture,
        )
        
        # Step 3: Create session
        session = self.session_manager.create_session(
            product=request.product,
            inventory=request.inventory,
            strategy=request.strategy,
            posture=posture,
            initial_offer=initial_offer,
            buyer_id=request.buyer_id,
            client_ip=client_ip,
        )
        
        # Step 4: Generate initial message
        conv_context = ConversationContext(
            round_number=0,
            max_rounds=request.strategy.max_rounds,
            mode=request.strategy.mode,
            product_name=request.product.product_name,
            quantity=request.inventory.requested_quantity,
            buyer_offered=None,
            our_offer=initial_offer,
        )
        message = self.conversation_agent.generate_initial_message(
            offer=initial_offer,
            context=conv_context,
        )
        
        return CreateSessionResponse(
            session_id=session.session_id,
            initial_offer=initial_offer,
            message=message,
            max_rounds=request.strategy.max_rounds,
            mode=request.strategy.mode,
            created_at=session.created_at,
        )
    
    def process_turn(
        self,
        session_id: UUID,
        buyer_offer: BuyerOffer,
    ) -> NegotiationTurnResponse:
        """
        Process a single negotiation turn.
        
        This:
        1. Validates session state
        2. Evaluates buyer offer
        3. Makes pricing decision
        4. Updates session state
        5. Generates response
        """
        # Step 1: Get session
        session = self.session_manager.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found or expired")
        
        if session.status != NegotiationStatus.ACTIVE:
            raise ValueError(f"Session {session_id} is not active: {session.status}")
        
        # Step 2: Check termination conditions
        if self._should_terminate(session):
            return self._terminate_session(session, NegotiationStatus.EXPIRED)
        
        # Step 3: Increment round
        session.pricing_state.current_round += 1
        session.pricing_state.buyer_history.append(buyer_offer.offered_price)
        
        # Step 4: Evaluate offer
        decision = self.pricing_agent.evaluate_offer(
            buyer_offer=buyer_offer,
            product=session.product,
            inventory=session.inventory,
            strategy=session.strategy,
            posture=session.posture,
            state=session.pricing_state,
        )
        
        # Step 5: Update state based on decision
        self._update_state(session, decision, buyer_offer)
        
        # Step 6: Generate response message
        conv_context = ConversationContext(
            round_number=session.pricing_state.current_round,
            max_rounds=session.strategy.max_rounds,
            mode=session.strategy.mode,
            product_name=session.product.product_name,
            quantity=session.inventory.requested_quantity,
            buyer_offered=buyer_offer.offered_price,
            our_offer=decision.counter_offer_price,
        )
        
        message = self.conversation_agent.generate_response(
            decision=decision,
            context=conv_context,
            floor_price=session.posture.reservation_price,
        )
        
        # Step 7: Determine final status
        status = self._determine_status(session, decision)
        can_continue = status == NegotiationStatus.ACTIVE
        
        # Step 8: Close session if needed
        if not can_continue:
            final_price = decision.accepted_price if decision.decision == OfferDecision.ACCEPT else None
            total_profit = decision.total_profit if decision.decision == OfferDecision.ACCEPT else None
            self.session_manager.close_session(
                session.session_id, status, final_price, total_profit
            )
        else:
            self.session_manager.update_session(session)
        
        return NegotiationTurnResponse(
            session_id=session.session_id,
            round_number=session.pricing_state.current_round,
            status=status,
            pricing=decision,
            message=message,
            can_continue=can_continue,
            rounds_remaining=max(0, session.strategy.max_rounds - session.pricing_state.current_round),
            timestamp=datetime.utcnow(),
        )
    
    def end_session(
        self,
        session_id: UUID,
        reason: str = "buyer_walked",
    ) -> SessionSummary:
        """
        End a negotiation session early.
        
        Use this when buyer walks away or for manual termination.
        """
        session = self.session_manager.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        
        status = NegotiationStatus.BUYER_WALKED
        self.session_manager.close_session(session_id, status)
        
        return self.session_manager.get_session_summary(session_id)
    
    def get_session(self, session_id: UUID) -> Optional[SessionSummary]:
        """Get session summary by ID."""
        return self.session_manager.get_session_summary(session_id)
    
    def get_analytics(self, session_id: UUID) -> Optional[NegotiationAnalytics]:
        """Get detailed analytics for a closed session."""
        session = self.session_manager.get_session(session_id)
        if session is None:
            return None
        
        state = session.pricing_state
        
        # Calculate concession
        total_concession = session.initial_offer - (session.final_price or session.initial_offer)
        concession_pct = (total_concession / session.initial_offer * 100
                        if session.initial_offer > 0 else Decimal("0"))
        
        # Calculate profit
        gross_profit = None
        profit_margin = None
        if session.final_price:
            gross_profit = session.final_price - session.product.cost_price
            if session.final_price > 0:
                profit_margin = (gross_profit / session.final_price * 100)
        
        # Calculate efficiency
        rounds_used = state.current_round if state else 0
        efficiency = Decimal(str(1 - (rounds_used / session.strategy.max_rounds)))
        
        # Count constraint violations
        violations = len([v for v in state.buyer_history 
                         if v < session.posture.walk_away_price]) if state else 0
        
        buyer_first = state.buyer_history[0] if state and state.buyer_history else Decimal("0")
        
        return NegotiationAnalytics(
            session_id=session.session_id,
            outcome=session.status,
            starting_price=session.initial_offer,
            final_price=session.final_price,
            buyer_first_offer=buyer_first,
            total_concession_given=total_concession,
            concession_percentage=concession_pct,
            rounds_used=rounds_used,
            rounds_available=session.strategy.max_rounds,
            efficiency_score=max(Decimal("0"), efficiency),
            gross_profit=gross_profit,
            profit_margin=profit_margin,
            mode_used=session.strategy.mode,
            constraint_violations_attempted=violations,
            walk_away_triggered=session.status == NegotiationStatus.REJECTED,
        )
    
    # ==========================================================================
    # Private Methods
    # ==========================================================================
    
    def _should_terminate(self, session: NegotiationSession) -> bool:
        """Check if session should terminate."""
        state = session.pricing_state
        
        # Max rounds reached
        if state.current_round >= session.strategy.max_rounds:
            return True
        
        return False
    
    def _terminate_session(
        self,
        session: NegotiationSession,
        status: NegotiationStatus,
    ) -> NegotiationTurnResponse:
        """Terminate session and return final response."""
        self.session_manager.close_session(session.session_id, status)
        
        conv_context = ConversationContext(
            round_number=session.pricing_state.current_round,
            max_rounds=session.strategy.max_rounds,
            mode=session.strategy.mode,
            product_name=session.product.product_name,
            quantity=session.inventory.requested_quantity,
            buyer_offered=None,
            our_offer=None,
        )
        
        message = self.conversation_agent.generate_session_expired(conv_context)
        
        # Create a minimal decision for the response
        final_decision = PricingDecision(
            decision=OfferDecision.REJECT,
            margin_percentage=Decimal("0"),
            profit_per_unit=Decimal("0"),
            total_profit=Decimal("0"),
            within_constraints=True,
            remaining_concession_budget=Decimal("0"),
            concession_percentage_used=Decimal("100"),
        )
        
        return NegotiationTurnResponse(
            session_id=session.session_id,
            round_number=session.pricing_state.current_round,
            status=status,
            pricing=final_decision,
            message=message,
            can_continue=False,
            rounds_remaining=0,
            timestamp=datetime.utcnow(),
        )
    
    def _update_state(
        self,
        session: NegotiationSession,
        decision: PricingDecision,
        buyer_offer: BuyerOffer,
    ) -> None:
        """Update session state based on decision."""
        state = session.pricing_state
        
        # Update buyer's last offer
        state.buyer_last_offer = buyer_offer.offered_price
        
        # Update concession used
        if decision.concession_made > 0:
            state.concession_used += decision.concession_made
        
        # Update our offer if countering
        if decision.decision == OfferDecision.COUNTER and decision.counter_offer_price:
            state.current_offer = decision.counter_offer_price
            state.offers_history.append(decision.counter_offer_price)
    
    def _determine_status(
        self,
        session: NegotiationSession,
        decision: PricingDecision,
    ) -> NegotiationStatus:
        """Determine session status based on decision."""
        if decision.decision == OfferDecision.ACCEPT:
            return NegotiationStatus.ACCEPTED
        
        if decision.decision == OfferDecision.REJECT:
            return NegotiationStatus.REJECTED
        
        # Check if this was the last round
        if session.pricing_state.current_round >= session.strategy.max_rounds:
            return NegotiationStatus.EXPIRED
        
        return NegotiationStatus.ACTIVE


# Global engine instance
_engine: Optional[NegotiationEngine] = None


def get_engine() -> NegotiationEngine:
    """Get or create global negotiation engine."""
    global _engine
    if _engine is None:
        _engine = NegotiationEngine()
    return _engine
