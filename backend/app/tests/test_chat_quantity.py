"""Regression tests for free-text chat quantity handling."""
from decimal import Decimal

from app.core import NegotiationEngine, SessionManager
from app.models import (
    ChatMessage,
    CreateSessionRequest,
    ProductData,
    InventoryContext,
    StrategicControls,
    NegotiationMode,
)


def _engine_without_llm() -> NegotiationEngine:
    engine = NegotiationEngine(session_manager=SessionManager())
    engine.llm.enabled = False
    return engine


def _session_request(quantity: int = 1, available: int = 20) -> CreateSessionRequest:
    return CreateSessionRequest(
        product=ProductData(
            product_id="basic-plan",
            product_name="Basic Plan",
            base_price=Decimal("50.00"),
            cost_price=Decimal("20.00"),
            min_acceptable_price=Decimal("30.00"),
        ),
        inventory=InventoryContext(
            available_quantity=available,
            requested_quantity=quantity,
        ),
        strategy=StrategicControls(
            mode=NegotiationMode.MAX_PROFIT,
            max_rounds=10,
        ),
    )


def test_quantity_only_fallback_updates_units_without_price_offer():
    engine = _engine_without_llm()
    created = engine.create_session(_session_request(quantity=1))

    response = engine.process_chat(
        created.session_id,
        ChatMessage(message="i watn 4 units"),
    )

    session = engine.session_manager.get_session(created.session_id)
    assert response.has_price_offer is False
    assert response.extracted_price is None
    assert session.inventory.requested_quantity == 4
    assert session.pricing_state.current_round == 0
    assert "Updated to 4 unit(s)" in response.message
    assert "$4.00" not in response.message


def test_second_quantity_change_is_not_treated_as_lowball_offer():
    engine = _engine_without_llm()
    created = engine.create_session(_session_request(quantity=1))

    first = engine.process_chat(created.session_id, ChatMessage(message="i watn 4 units"))
    second = engine.process_chat(created.session_id, ChatMessage(message="I want 5 units"))

    session = engine.session_manager.get_session(created.session_id)
    assert first.has_price_offer is False
    assert second.has_price_offer is False
    assert session.inventory.requested_quantity == 5
    assert session.pricing_state.current_round == 0
    assert "Updated to 5 unit(s)" in second.message
    assert "below what I can consider" not in second.message


def test_price_after_quantity_change_uses_new_quantity_for_profit():
    engine = _engine_without_llm()
    created = engine.create_session(_session_request(quantity=1))

    engine.process_chat(created.session_id, ChatMessage(message="I want 5 units"))
    response = engine.process_chat(created.session_id, ChatMessage(message="$40"))

    session = engine.session_manager.get_session(created.session_id)
    assert response.has_price_offer is True
    assert response.extracted_price == Decimal("40.0")
    assert session.inventory.requested_quantity == 5
    assert response.pricing.total_profit == (
        response.pricing.profit_per_unit * Decimal("5")
    )
    assert response.pricing.concession_percentage_used >= Decimal("0")


def test_quantity_above_stock_is_rejected_without_state_change():
    engine = _engine_without_llm()
    created = engine.create_session(_session_request(quantity=1, available=3))

    response = engine.process_chat(
        created.session_id,
        ChatMessage(message="I want 5 units"),
    )

    session = engine.session_manager.get_session(created.session_id)
    assert response.has_price_offer is False
    assert session.inventory.requested_quantity == 1
    assert "only have 3 unit(s) available" in response.message


def test_llm_quantity_misread_as_same_price_is_corrected():
    engine = _engine_without_llm()
    engine.llm.enabled = True
    created = engine.create_session(_session_request(quantity=1))

    def fake_understand(*_args, **_kwargs):
        return (True, 4.0, None, None, False, None, False)

    engine._understand_chat = fake_understand
    response = engine.process_chat(created.session_id, ChatMessage(message="I want 4 units"))

    session = engine.session_manager.get_session(created.session_id)
    assert response.has_price_offer is False
    assert session.inventory.requested_quantity == 4
    assert session.pricing_state.current_round == 0


def test_llm_quantity_plus_real_price_is_preserved():
    engine = _engine_without_llm()
    engine.llm.enabled = True
    created = engine.create_session(_session_request(quantity=1))

    def fake_understand(*_args, **_kwargs):
        return (True, 45.0, None, None, True, 4, False)

    engine._understand_chat = fake_understand
    response = engine.process_chat(
        created.session_id,
        ChatMessage(message="I want 4 units at 45 each"),
    )

    session = engine.session_manager.get_session(created.session_id)
    assert response.has_price_offer is True
    assert response.extracted_price == Decimal("45.0")
    assert session.inventory.requested_quantity == 4
    assert session.pricing_state.current_round == 1
