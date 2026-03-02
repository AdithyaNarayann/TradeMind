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
    ChatMessage,
    ChatResponse,
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
from ..infrastructure.llm.openai_client import get_llm_client
from ..infrastructure.llm import prompt_templates as llm_prompts
from .session import SessionManager, NegotiationSession, get_session_manager

import json
import structlog

logger = structlog.get_logger(__name__)


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
        self.llm = get_llm_client()

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
            strategy=request.strategy,
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

    def process_chat(
        self,
        session_id: UUID,
        chat_message: ChatMessage,
    ) -> ChatResponse:
        """
        Process a free-text chat message from the buyer.

        Uses LLM to understand the message:
        - If it contains a price offer -> route to process_turn()
        - If buyer changes quantity -> update session & engine state, recalc prices
        - If it's just conversation -> reply in character
        """
        # Step 1: Get session
        session = self.session_manager.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found or expired")

        if session.status != NegotiationStatus.ACTIVE:
            raise ValueError(f"Session {session_id} is not active: {session.status}")

        # Step 2: Build negotiation history for context
        state = session.pricing_state
        history_parts = []
        for i, (our, buyer) in enumerate(zip(
            state.offers_history if state else [],
            state.buyer_history if state else []
        )):
            history_parts.append(f"R{i+1}: Seller=${our}, Buyer=${buyer}")
        if state and len(state.offers_history) > len(state.buyer_history):
            history_parts.append(f"Current seller offer: ${state.offers_history[-1]}")
        history_str = "; ".join(history_parts) if history_parts else "Opening round — no offers exchanged yet"

        current_offer = str(state.current_offer) if state else str(session.initial_offer)

        # Step 3: Use LLM to understand buyer's message
        if self.llm.enabled:
            try:
                extracted = self._understand_chat(chat_message.message, session, current_offer, history_str)
                if extracted is not None:
                    has_price, unit_price, total_price, reply, has_qty_change, new_qty = extracted

                    # Handle quantity change (with or without a price offer)
                    if has_qty_change and new_qty is not None and new_qty > 0:
                        self._apply_quantity_change(session, new_qty)

                    if has_price and (
                        (unit_price is not None and unit_price > 0)
                        or (total_price is not None and total_price > 0)
                    ):
                        # Resolve effective per-unit price
                        qty = session.inventory.requested_quantity
                        if unit_price is not None and unit_price > 0:
                            effective_price = unit_price
                        elif total_price is not None and total_price > 0 and qty > 0:
                            effective_price = round(total_price / qty, 2)
                        else:
                            effective_price = None

                        if effective_price is not None and effective_price > 0:
                            # ── Sanity: cap at base price ──────────────
                            #   No rational buyer offers above the asking price.
                            #   If extracted price > base, it's almost certainly
                            #   a mistype or LLM parsing error. Clamp to base.
                            base = float(session.product.base_price)
                            if effective_price > base:
                                effective_price = base

                            # Store buyer message in history
                            state.chat_history.append({"role": "Buyer", "text": chat_message.message})

                            # Route to pricing engine
                            buyer_offer = BuyerOffer(
                                offered_price=Decimal(str(effective_price)),
                                message=chat_message.message,
                                offered_quantity=new_qty if has_qty_change and new_qty else None,
                            )
                            turn_response = self.process_turn(session_id, buyer_offer)

                            # Store seller response in history
                            state.chat_history.append({"role": "Seller", "text": turn_response.message})

                            return ChatResponse(
                                session_id=session_id,
                                message=turn_response.message,
                                has_price_offer=True,
                                extracted_price=Decimal(str(effective_price)),
                                round_number=turn_response.round_number,
                                status=turn_response.status,
                                pricing=turn_response.pricing,
                                can_continue=turn_response.can_continue,
                                rounds_remaining=turn_response.rounds_remaining,
                            )
                    elif has_qty_change and new_qty is not None and new_qty > 0:
                        # Pure quantity change — acknowledge and show updated pricing
                        eng = state.engine_state
                        if eng:
                            # Use bulk_target_price (reflects volume discount)
                            per_unit = eng.bulk_target_price
                            if eng.counter_history:
                                # If prior counters are below bulk target, honour them
                                per_unit = min(eng.counter_history[-1], per_unit)
                        else:
                            # Engine not initialized yet — compute bulk target from product data
                            from ..agents.negotiation_engine import compute_bulk_target_price
                            mode = session.strategy.mode.value if session.strategy else "MAX_PROFIT"
                            per_unit = compute_bulk_target_price(
                                float(session.product.base_price), new_qty, mode,
                            )
                        qty_msg = (
                            f"Updated to {new_qty} unit(s). "
                            f"Our current offer is ${per_unit:.2f} per unit "
                            f"(${per_unit * new_qty:.2f} total for {new_qty} units). "
                            f"What price would you like to offer?"
                        )
                        # Store in chat history
                        state.chat_history.append({"role": "Buyer", "text": chat_message.message})
                        state.chat_history.append({"role": "Seller", "text": qty_msg})
                        return ChatResponse(
                            session_id=session_id,
                            message=qty_msg,
                            has_price_offer=False,
                        )
                    else:
                        # Pure conversation — return LLM reply
                        reply_text = reply or "Could you please make a specific price offer?"
                        state.chat_history.append({"role": "Buyer", "text": chat_message.message})
                        state.chat_history.append({"role": "Seller", "text": reply_text})
                        return ChatResponse(
                            session_id=session_id,
                            message=reply_text,
                            has_price_offer=False,
                        )
            except Exception as e:
                logger.error("chat_understanding_error", error=str(e))

        # Fallback: try simple regex extraction
        import re
        match = re.search(r'\$?\s?(\d+(?:\.\d{1,2})?)', chat_message.message)
        if match:
            price = float(match.group(1))
            if price > 0:
                buyer_offer = BuyerOffer(
                    offered_price=Decimal(str(price)),
                    message=chat_message.message,
                )
                turn_response = self.process_turn(session_id, buyer_offer)
                return ChatResponse(
                    session_id=session_id,
                    message=turn_response.message,
                    has_price_offer=True,
                    extracted_price=Decimal(str(price)),
                    round_number=turn_response.round_number,
                    status=turn_response.status,
                    pricing=turn_response.pricing,
                    can_continue=turn_response.can_continue,
                    rounds_remaining=turn_response.rounds_remaining,
                )

        # No price found and LLM failed — generic reply
        return ChatResponse(
            session_id=session_id,
            message=f"Thank you for your interest in {session.product.product_name}! Our current offer is ${current_offer} per unit. Feel free to make a price offer and we'll see what we can work out.",
            has_price_offer=False,
        )

    def _apply_quantity_change(
        self,
        session: NegotiationSession,
        new_qty: int,
    ) -> None:
        """
        Update session and engine state when buyer changes quantity mid-chat.

        Recalculates dynamic floor, concession budget, and scarcity
        based on the new quantity.
        """
        from ..agents.negotiation_engine import (
            _compute_dynamic_floor,
            _apply_psim,
            compute_bulk_target_price,
            TUNING,
        )

        # Update session inventory
        session.inventory.requested_quantity = new_qty

        # Update PRANE-X engine state
        eng = session.pricing_state.engine_state
        if eng is None:
            return

        old_qty = eng.quantity
        eng.quantity = new_qty

        # Recalculate floor (bulk discount changes with quantity)
        eng.dynamic_floor = _compute_dynamic_floor(eng)
        eng.dynamic_floor = _apply_psim(eng)

        # Recalculate scarcity lock
        T = TUNING
        eng.scarcity_locked = (
            (eng.available_inventory - new_qty) < T["scarcity_stock_threshold"]
        )
        if eng.scarcity_locked:
            eng.dynamic_floor = round(
                min(eng.dynamic_floor * (1 + T["scarcity_floor_lift"]), eng.base_price),
                2,
            )

        # Recalculate bulk target price for new quantity
        eng.bulk_target_price = max(
            compute_bulk_target_price(eng.base_price, new_qty, eng.mode),
            eng.dynamic_floor,
        )

        # ── Quantity change: reset counter progress ────────────
        #   The deal fundamentally changed: old counters don't reflect
        #   the correct bulk discount for the new quantity.
        #   On decrease: old bulk-discounted counters are too low.
        #   On increase: old counters lack the new volume discount.
        #   Either way, clear and let concession restart from the
        #   correct bulk_target_price.
        if new_qty != old_qty:
            # Only clear if counter_history has stale entries above bulk target
            # (or on decrease, always clear to prevent exploit)
            if new_qty < old_qty or (
                eng.counter_history and eng.counter_history[-1] > eng.bulk_target_price + 0.01
            ):
                eng.counter_history.clear()
                eng.final_offer_issued = False
                eng.consecutive_stagnant = 0
                eng.retrograde_count = 0
                eng.good_faith_after_final = 0

                # Reset round tracking — counter restarts from
                # bulk_target, so stale round pressure would inflate
                # the first concession step.  Cap max_rounds at
                # remaining rounds (min 2) to prevent exploitation.
                eng.offer_history.clear()
                rounds_remaining = max(eng.max_rounds - eng.current_round, 2)
                eng.max_rounds = rounds_remaining
                eng.current_round = 0

        # Recalculate concession budget for new quantity
        new_total_budget = max((eng.base_price - eng.dynamic_floor) * new_qty, 0.0)

        # Full budget reset on any quantity change
        if new_qty != old_qty:
            ratio_used = 0.0
        elif eng.total_concession_budget > 0:
            ratio_used = 1.0 - (eng.remaining_concession_budget / eng.total_concession_budget)
        else:
            ratio_used = 0.0

        eng.total_concession_budget = new_total_budget
        eng.remaining_concession_budget = max(new_total_budget * (1.0 - ratio_used), 0.0)

        logger.info(
            "quantity_changed",
            old_qty=old_qty,
            new_qty=new_qty,
            new_floor=eng.dynamic_floor,
            new_budget=eng.total_concession_budget,
        )

    def _understand_chat(
        self,
        buyer_message: str,
        session: NegotiationSession,
        current_offer: str,
        history_str: str,
    ) -> Optional[tuple]:
        """
        Use LLM to understand buyer's free-text message.

        Returns: (has_price, unit_price, total_price, reply, has_qty_change, extracted_qty)
        unit_price and total_price are mutually exclusive; at most one is set.
        """
        state = session.pricing_state

        # Build recent conversation messages for context
        msg_parts = []
        for msg in (state.chat_history or [])[-8:]:  # last 8 messages (4 exchanges)
            role = msg.get("role", "")
            text = msg.get("text", "")
            msg_parts.append(f"  {role}: {text}")
        conversation_messages = "\n".join(msg_parts) if msg_parts else ""

        prompt = llm_prompts.build_chat_understanding_prompt(
            buyer_message=buyer_message,
            product_name=session.product.product_name,
            base_price=str(session.product.base_price),
            our_last_offer=current_offer,
            current_round=state.current_round if state else 0,
            max_rounds=session.strategy.max_rounds,
            mode=session.strategy.mode.value,
            negotiation_history=history_str,
            current_quantity=session.inventory.requested_quantity,
            conversation_messages=conversation_messages,
        )

        result = self.llm.generate_sync(
            system_prompt=llm_prompts.CHAT_UNDERSTANDING_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3,
        )

        if not result.success:
            return None

        try:
            content = result.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            data = json.loads(content)
            has_price = data.get("has_price", False)

            # Parse unit / total price (new schema)
            unit_price = data.get("extracted_unit_price")
            total_price = data.get("extracted_total_price")

            # Backward compat: if old-style `extracted_price` is present and
            # neither new field was set, treat it as unit price.
            if unit_price is None and total_price is None:
                legacy = data.get("extracted_price")
                if legacy is not None:
                    unit_price = legacy

            reply = data.get("reply", "")
            has_qty_change = data.get("has_quantity_change", False)
            extracted_qty = data.get("extracted_quantity")

            # Validate quantity
            if extracted_qty is not None:
                try:
                    extracted_qty = int(extracted_qty)
                    if extracted_qty <= 0:
                        extracted_qty = None
                        has_qty_change = False
                except (ValueError, TypeError):
                    extracted_qty = None
                    has_qty_change = False

            return (has_price, unit_price, total_price, reply, has_qty_change, extracted_qty)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("chat_understanding_parse_error", error=str(e))
            return None

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
