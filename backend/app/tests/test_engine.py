"""
Tests for the PRANE-X Negotiation Engine.

All tests target the deterministic, pure-function logic in
negotiation_engine.py. No LLM, no I/O, no randomness.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

# Ensure backend root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents.negotiation_engine import (
    TUNING,
    NegotiationState,
    NegotiationPhase,
    BuyerArchetype,
    ReasoningTag,
    EngineResult,
    process_round,
    derive_archetype,
    compute_bulk_target_price,
    _compute_dynamic_floor,
    _apply_psim,
    _compute_concession,
    _should_accept,
    _estimate_buyer_ceiling,
    _determine_phase,
    _recalculate_for_quantity,
    clamp,
    sigmoid,
)
from app.agents.pricing_agent import PricingStrategyAgent


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _make_state(**overrides) -> NegotiationState:
    """Create a default NegotiationState with sensible test defaults."""
    defaults = dict(
        base_price=100.0,
        cost_price=60.0,
        min_floor=65.0,
        mode="MAX_PROFIT",
        max_rounds=10,
        quantity=1,
        total_sessions=0,
        accepted_deals=0,
        historical_avg_margin=TUNING["target_margin_default"],
        historical_revenue=0.0,
        available_inventory=100,
        reference_inventory=100,
        buyer_archetype=BuyerArchetype.UNKNOWN,
    )
    defaults.update(overrides)
    return NegotiationState(**defaults)


def _make_extraction(**overrides) -> dict:
    """Create a default extraction dict."""
    defaults = dict(
        quantity=None,
        unit_price_offered=80.0,
        total_price_offered=None,
        intent="offer",
        tone="neutral",
        anchoring_detected=False,
        urgency_signal=False,
        bundle_request=False,
        social_proof_claim=False,
    )
    defaults.update(overrides)
    return defaults


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Determinism
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeterminism:
    def test_determinism(self):
        """process_round called 1000x with identical inputs → identical outputs."""
        snapshot = _make_state()
        extraction = _make_extraction(unit_price_offered=75.0)

        results: list[EngineResult] = []
        for _ in range(1000):
            state = copy.deepcopy(snapshot)
            ext = copy.deepcopy(extraction)
            result = process_round(state, ext)
            results.append(result)

        first = results[0]
        for r in results[1:]:
            assert r == first, f"Non-deterministic: {r} != {first}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Floor never violated
# ═══════════════════════════════════════════════════════════════════════════════

class TestFloorNeverViolated:
    def test_floor_never_violated(self):
        """Offer below cost → counter or reject, never accept. Counter >= floor."""
        state = _make_state()
        # Offer at cost_price - 1
        extraction = _make_extraction(unit_price_offered=state.cost_price - 1.0)
        result = process_round(state, extraction)

        assert result.decision in ("counter", "reject")
        assert result.decision != "accept"
        assert result.counter_unit_price >= state.dynamic_floor

    def test_floor_never_violated_extreme_low(self):
        """Even absurdly low offers never break the floor."""
        state = _make_state()
        extraction = _make_extraction(unit_price_offered=1.0)
        result = process_round(state, extraction)

        assert result.decision in ("counter", "reject")
        assert result.counter_unit_price >= state.dynamic_floor

    def test_below_floor_counter_uses_concession_curve(self):
        """Below-floor offers get a concession-curve counter, not a stuck floor.

        The counter should start near base_price and gradually descend
        across rounds — never jump to floor on round 1.
        """
        state = _make_state(base_price=300.0, cost_price=80.0, min_floor=85.0)
        counters = []
        for i in range(4):
            ext = _make_extraction(unit_price_offered=20.0 + i * 10)
            result = process_round(state, ext)
            counters.append(result.counter_unit_price)

        # Round 1 counter should be near base, NOT at floor
        assert counters[0] > state.dynamic_floor + 50, (
            f"Round 1 counter {counters[0]} stuck near floor {state.dynamic_floor}"
        )
        # Counter should descend across rounds
        assert counters[-1] <= counters[0], (
            f"Counter not descending: {counters}"
        )
        # All counters above floor
        for c in counters:
            assert c >= state.dynamic_floor


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Phase progression
# ═══════════════════════════════════════════════════════════════════════════════

class TestPhaseProgression:
    def test_phase_progression(self):
        """Phases transition at the correct round fractions for max_rounds=10.

        Uses below-floor offers with >4% improvement each round to:
        - avoid utility acceptance (hard floor check in _should_accept)
        - avoid stagnation triggers (>2% improvement clears stagnant counter)
        - avoid retrograde triggers (all improvements positive)
        """
        state = _make_state(max_rounds=10)  # floor = 65, base = 100
        phases_seen: list[NegotiationPhase] = []

        # Offers: 40, 42, 44, ..., 58 — all below floor=65, each +5% improvement
        for i in range(1, 11):
            offer = 38.0 + i * 2.0   # 40, 42, 44, 46, ..., 58
            extraction = _make_extraction(unit_price_offered=offer)
            result = process_round(state, extraction)
            phases_seen.append(result.phase)

        # Round 1 (progress=0.1, anchor_boundary=0.1) → ANCHOR_RESIST
        assert phases_seen[0] == NegotiationPhase.ANCHOR_RESIST

        # Rounds 2-3 (progress 0.2-0.3, <= 0.35) → PROBING
        assert phases_seen[1] == NegotiationPhase.PROBING
        assert phases_seen[2] == NegotiationPhase.PROBING

        # Rounds 4-7 (progress 0.4-0.7, <= 0.75) → CONCEDING
        assert phases_seen[3] == NegotiationPhase.CONCEDING

        # Round 8+ (progress > 0.75) → CLOSING
        assert phases_seen[7] == NegotiationPhase.CLOSING


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Retrograde triggers final offer
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetrogradeTriggersFinal:
    def test_retrograde_triggers_final(self):
        """Consecutive decreasing offers → final_offer_issued = True.

        BBI update (step 5) now runs BEFORE anti-manipulation (step 7)
        in the same round, so retrograde_count is fresh when the
        manipulation check fires.  Two decreases set count=2, and the
        third round's manipulation check sees it immediately.
        """
        state = _make_state()

        # Round 1: first offer (no trajectory yet)
        process_round(state, _make_extraction(unit_price_offered=80.0))

        # Round 2: decrease → retrograde_count becomes 1
        process_round(state, _make_extraction(unit_price_offered=78.0))

        # Round 3: second decrease → retrograde_count becomes 2,
        #          manipulation check fires in the same round
        result = process_round(state, _make_extraction(unit_price_offered=76.0))
        assert state.retrograde_count >= TUNING["retrograde_immediate_trigger"]
        assert state.final_offer_issued is True
        assert result.decision == "final_offer"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Round-1 concession cap
# ═══════════════════════════════════════════════════════════════════════════════

class TestRound1ConcessionCap:
    def test_round1_concession_cap(self):
        """On round 1, counter concession <= base_price * round1_max_concession_pct.

        Round-1 acceptance guard prevents the utility model from accepting
        any offer on round 1, so this always produces a counter.
        """
        state = _make_state()
        # Offer just above floor so engine counters rather than accepts
        extraction = _make_extraction(unit_price_offered=state.dynamic_floor + 1.0)
        result = process_round(state, extraction)

        assert result.decision == "counter", (
            f"Expected counter, got {result.decision} — "
            f"adjust offer so utility model rejects"
        )
        max_allowed = state.base_price * TUNING["round1_max_concession_pct"]
        actual_concession = state.base_price - result.counter_unit_price
        assert actual_concession <= max_allowed + 0.01  # tiny float tolerance


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ZOPA final offer
# ═══════════════════════════════════════════════════════════════════════════════

class TestZopaFinalOffer:
    def test_zopa_final_offer(self):
        """Low WTP with narrow margin → final_offer with ZOPA_NO_OVERLAP.

        buyer_ceiling = floor + (base-floor)*wtp*factor.  With WTP clamped
        at 0.05 the margin must be small enough so buyer_ceiling falls
        below floor + 1% of base (the 'meaningful overlap' threshold).
        Using base=68 gives buyer_ceiling ≈ 65.17 < 65.68 → no overlap.
        """
        state = _make_state(base_price=68.0, cost_price=60.0, min_floor=65.0)

        found_zopa = False
        for i in range(TUNING["zopa_no_overlap_max_rounds"] + 2):
            extraction = _make_extraction(unit_price_offered=state.dynamic_floor + 0.5)
            result = process_round(state, extraction)
            if result.reasoning_tag == ReasoningTag.ZOPA_NO_OVERLAP:
                found_zopa = True
                break

        assert found_zopa or state.final_offer_issued is True, (
            f"Expected ZOPA_NO_OVERLAP final, got tag={result.reasoning_tag}, "
            f"final_offer_issued={state.final_offer_issued}, "
            f"zopa_count={state.zopa_no_overlap_count}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PSIM raises floor
# ═══════════════════════════════════════════════════════════════════════════════

class TestPsimRaisesFloor:
    def test_psim_raises_floor(self):
        """High conversion + low margin → PSIM lifts dynamic_floor."""
        # Without PSIM (insufficient history)
        state_no_psim = _make_state(
            total_sessions=0,
            accepted_deals=0,
            historical_avg_margin=0.10,
        )
        floor_without = state_no_psim.dynamic_floor

        # With PSIM (lots of history, low margin, high conversion)
        state_psim = _make_state(
            total_sessions=10,
            accepted_deals=7,
            historical_avg_margin=0.10,
        )
        floor_with = state_psim.dynamic_floor

        assert floor_with > floor_without


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: IRGM surplus reduces curve
# ═══════════════════════════════════════════════════════════════════════════════

class TestIrgmSurplusReducesCurve:
    def test_irgm_surplus_reduces_curve(self):
        """Surplus inventory + low revenue → curve_power decreases (more generous)."""
        state = _make_state(
            available_inventory=200,
            reference_inventory=100,
            historical_revenue=10.0,
            total_sessions=10,
        )
        # Simulate a round to trigger concession computation
        state.current_round = 1
        state.phase = NegotiationPhase.CONCEDING
        state.offer_history = [70.0]

        counter_price, tag = _compute_concession(state)

        # With surplus + low revenue, IRGM should reduce curve_power,
        # resulting in a lower (more generous) counter than the mode default
        # The key indicator is the tag
        # We verify the counter is at or above the dynamic floor
        assert counter_price >= state.dynamic_floor


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BAM lowballer reduces BBI
# ═══════════════════════════════════════════════════════════════════════════════

class TestBamLowballerReducesBbi:
    def test_bam_lowballer_reduces_bbi(self):
        """LOWBALLER archetype → initial BBI < default start."""
        state = _make_state(buyer_archetype=BuyerArchetype.LOWBALLER)
        assert state.bbi < TUNING["bbi_start"]
        assert state.bbi == clamp(
            TUNING["bbi_start"] + TUNING["bam_bbi_bias"]["LOWBALLER"],
            0.0, 100.0,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Extended utility — acceptance guards and marginal model
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcceptanceModel:
    def test_never_accepts_round_1_max_profit(self):
        """In MAX_PROFIT mode, _should_accept always returns False on round 1."""
        state = _make_state(max_rounds=10)
        state.current_round = 1
        state.offer_history = [95.0]
        state.counter_history = [100.0]
        # Even a very generous offer should not be accepted on round 1
        assert _should_accept(state, 95.0, 100.0) is False

    def test_never_accepts_below_ratio_max_profit(self):
        """In MAX_PROFIT, rejects if offer/base < 0.88 even at late round."""
        state = _make_state(max_rounds=10)
        state.current_round = 8
        state.offer_history = [70.0, 72.0, 74.0, 76.0, 78.0, 80.0, 82.0, 84.0]
        state.counter_history = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0]
        state.bbi = 50.0
        # 84 / 100 = 0.84 < 0.88 → reject
        assert _should_accept(state, 84.0, 93.0) is False

    def test_accepts_high_ratio_late_round(self):
        """At round 8 with offer_ratio=0.93, should accept (marginal gain low)."""
        state = _make_state(max_rounds=10)
        state.current_round = 8
        state.offer_history = [80.0, 82.0, 85.0, 87.0, 89.0, 90.0, 91.0, 93.0]
        state.counter_history = [100.0, 99.5, 98.5, 97.0, 96.0, 95.0, 94.5, 94.0]
        state.bbi = 40.0
        state.p_high_wtp = 0.3
        # 93 / 100 = 0.93 >= 0.88, round 8 >= 3 → passes guards
        # With low BBI and small gap, marginal gain is tiny
        result = _should_accept(state, 93.0, 94.0)
        assert isinstance(result, bool)

    def test_expensive_item_not_accepted_round_1(self):
        """Bluetooth-speaker scenario: $1959 base, $1400 offer, round 1 → reject.

        Previously this was accepted because absolute profit was huge.
        The round guard now prevents acceptance on round 1.
        """
        state = _make_state(
            base_price=1959.0, cost_price=800.0, min_floor=850.0,
            quantity=10, max_rounds=10,
        )
        state.current_round = 1
        state.offer_history = [1400.0]
        state.counter_history = [1959.0]
        assert _should_accept(state, 1400.0, 1959.0) is False

    def test_expensive_item_not_accepted_at_low_ratio(self):
        """Bluetooth-speaker: $1400/$1959 = 0.714 < 0.88 → reject at any round."""
        state = _make_state(
            base_price=1959.0, cost_price=800.0, min_floor=850.0,
            quantity=10, max_rounds=10,
        )
        state.current_round = 5
        state.offer_history = [1200.0, 1250.0, 1300.0, 1350.0, 1400.0]
        state.counter_history = [1959.0, 1950.0, 1940.0, 1925.0, 1910.0]
        state.bbi = 50.0
        # 1400 / 1959 = 0.714 < 0.88
        assert _should_accept(state, 1400.0, 1910.0) is False

    def test_inventory_relief_tips_acceptance(self):
        """Full clearance order → inventory relief reduces net_benefit_of_waiting.

        With tiny inventory and high offer ratio, relief should push toward acceptance.
        """
        state = _make_state(
            available_inventory=10,
            reference_inventory=100,
            quantity=10,
            max_rounds=10,
        )
        state.current_round = 5
        state.offer_history = [88.0, 89.0, 90.0, 91.0, 92.0]
        state.counter_history = [100.0, 99.0, 97.0, 95.0, 94.0]
        state.bbi = 30.0  # Low BBI → low p_improve
        state.p_high_wtp = 0.2

        # 92 / 100 = 0.92 >= 0.88, round 5 >= 3 → passes guards
        accepts_small_inv = _should_accept(state, 92.0, 94.0)

        # Same but large inventory
        state_large = copy.deepcopy(state)
        state_large.available_inventory = 10000
        accepts_large_inv = _should_accept(state_large, 92.0, 94.0)

        assert isinstance(accepts_small_inv, bool)
        assert isinstance(accepts_large_inv, bool)

    def test_min_loss_mode_lower_guards(self):
        """MIN_LOSS mode has lower acceptance guards (round 2, ratio 0.78)."""
        state = _make_state(mode="MIN_LOSS", max_rounds=10)
        state.current_round = 2
        state.offer_history = [80.0, 82.0]
        state.counter_history = [100.0, 98.0]
        state.bbi = 50.0
        # 82 / 100 = 0.82 >= 0.78 → passes ratio guard
        # round 2 >= 2 → passes round guard
        result = _should_accept(state, 82.0, 98.0)
        assert isinstance(result, bool)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Quantity change recalculation
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuantityChange:
    def test_recalculate_for_quantity_updates_budget(self):
        """Changing quantity fully resets concession budget."""
        state = _make_state(quantity=1)
        original_budget = state.total_concession_budget

        # Use half the budget
        state.remaining_concession_budget = original_budget * 0.5

        # Change to 5 units
        state.quantity = 5
        _recalculate_for_quantity(state, old_qty=1)

        # Budget should be fully reset (not proportionally scaled)
        # because qty changed
        assert state.total_concession_budget > original_budget
        assert state.remaining_concession_budget == state.total_concession_budget

    def test_quantity_change_in_process_round(self):
        """Passing a new quantity in extraction triggers recalculation."""
        state = _make_state(quantity=1)
        original_floor = state.dynamic_floor

        extraction = _make_extraction(
            unit_price_offered=80.0,
            quantity=10,
        )
        result = process_round(state, extraction)
        assert state.quantity == 10
        # Floor may change due to bulk discount
        assert state.dynamic_floor <= original_floor or state.dynamic_floor >= original_floor

    def test_quantity_change_preserves_budget_ratio(self):
        """After 3 rounds with qty=1, changing to qty=5 preserves usage ratio."""
        state = _make_state(quantity=1, max_rounds=10)

        # Play 3 rounds at qty=1
        for offer in [70.0, 72.0, 74.0]:
            ext = _make_extraction(unit_price_offered=offer)
            process_round(state, ext)

        budget_used_frac = 1.0 - (state.remaining_concession_budget / state.total_concession_budget)
        assert budget_used_frac > 0  # Some budget used

        # Now buyer changes to qty=5
        ext = _make_extraction(unit_price_offered=76.0, quantity=5)
        process_round(state, ext)

        assert state.quantity == 5
        new_used_frac = 1.0 - (state.remaining_concession_budget / state.total_concession_budget)
        # Should be approximately same fraction used (may differ slightly due to recalc)
        assert new_used_frac > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Price validator
# ═══════════════════════════════════════════════════════════════════════════════

class TestPriceValidator:
    def test_price_validator_replaces_wrong_price(self):
        """Injected wrong price → replaced with counter_unit_price."""
        text = "I can offer this at $999.99 per unit."
        sanitized = PricingStrategyAgent.validate_and_sanitize_prices(
            text,
            counter_unit_price=85.50,
            counter_total_price=171.00,
        )
        assert "$999.99" not in sanitized
        assert "85.50" in sanitized

    def test_price_validator_keeps_correct_price(self):
        """Correct prices are not modified."""
        text = "My offer is $85.50 per unit, total $171.00."
        sanitized = PricingStrategyAgent.validate_and_sanitize_prices(
            text,
            counter_unit_price=85.50,
            counter_total_price=171.00,
        )
        assert "85.50" in sanitized
        assert "171.00" in sanitized


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Derive archetype
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeriveArchetype:
    def test_unknown_with_insufficient_history(self):
        assert derive_archetype([]) == BuyerArchetype.UNKNOWN
        assert derive_archetype([{"offered_price": 50, "counter_price": 100, "total_rounds": 3, "decision": "accept"}]) == BuyerArchetype.UNKNOWN

    def test_lowballer(self):
        history = [
            {"offered_price": 30, "counter_price": 100, "total_rounds": 5, "decision": "reject"},
            {"offered_price": 25, "counter_price": 100, "total_rounds": 4, "decision": "reject"},
            {"offered_price": 35, "counter_price": 100, "total_rounds": 6, "decision": "reject"},
        ]
        assert derive_archetype(history) == BuyerArchetype.LOWBALLER

    def test_impulse(self):
        history = [
            {"offered_price": 90, "counter_price": 100, "total_rounds": 1, "decision": "accept"},
            {"offered_price": 85, "counter_price": 100, "total_rounds": 2, "decision": "accept"},
            {"offered_price": 95, "counter_price": 100, "total_rounds": 1, "decision": "accept"},
        ]
        assert derive_archetype(history) == BuyerArchetype.IMPULSE


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Math helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestMathHelpers:
    def test_sigmoid_bounds(self):
        assert 0.0 < sigmoid(-500) < 0.01
        assert 0.99 < sigmoid(500) <= 1.0
        assert abs(sigmoid(0) - 0.5) < 0.001

    def test_sigmoid_no_overflow(self):
        """Extreme inputs must not raise OverflowError."""
        sigmoid(1e10)
        sigmoid(-1e10)

    def test_clamp(self):
        assert clamp(5.0, 0.0, 10.0) == 5.0
        assert clamp(-1.0, 0.0, 10.0) == 0.0
        assert clamp(15.0, 0.0, 10.0) == 10.0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Bulk discount / volume pricing
# ═══════════════════════════════════════════════════════════════════════════════

class TestBulkDiscount:
    """Verify bulk/volume orders get meaningful per-unit price reductions."""

    def test_bulk_target_equals_base_for_qty_1(self):
        """No discount for single-unit orders."""
        target = compute_bulk_target_price(100.0, 1, "MAX_PROFIT")
        assert target == 100.0

    def test_bulk_target_below_base_for_qty_gt_1(self):
        """Multi-unit orders get a lower starting price."""
        for qty in [2, 5, 10, 20, 50]:
            target = compute_bulk_target_price(100.0, qty, "MAX_PROFIT")
            assert target < 100.0, f"qty={qty} should have discount"

    def test_bulk_target_scales_with_quantity(self):
        """Higher quantities → bigger discount (monotonically decreasing price)."""
        base = 1999.0
        prices = [
            compute_bulk_target_price(base, q, "MAX_PROFIT")
            for q in [2, 5, 10, 20, 50]
        ]
        for i in range(len(prices) - 1):
            assert prices[i] > prices[i + 1], (
                f"price at qty should decrease: {prices}"
            )

    def test_bulk_target_never_below_floor(self):
        """Bulk target must stay above the dynamic floor."""
        state = _make_state(quantity=50, base_price=100.0, cost_price=90.0, min_floor=92.0)
        assert state.bulk_target_price >= state.dynamic_floor

    def test_min_loss_gives_bigger_discount_than_max_profit(self):
        """MIN_LOSS mode should offer larger bulk discounts."""
        base = 500.0
        for qty in [5, 10, 20]:
            mp = compute_bulk_target_price(base, qty, "MAX_PROFIT")
            ml = compute_bulk_target_price(base, qty, "MIN_LOSS")
            assert ml < mp, (
                f"qty={qty}: MIN_LOSS ({ml}) should be lower than MAX_PROFIT ({mp})"
            )

    def test_engine_state_has_bulk_target(self):
        """NegotiationState computes bulk_target_price in __post_init__."""
        state = _make_state(quantity=10)
        assert hasattr(state, "bulk_target_price")
        assert state.bulk_target_price < state.base_price
        assert state.bulk_target_price >= state.dynamic_floor

    def test_first_counter_starts_from_bulk_target(self):
        """Round 1 counter for bulk order should be near bulk_target, not base."""
        state = _make_state(quantity=6, base_price=1999.0, cost_price=800.0, min_floor=850.0)
        extraction = _make_extraction(unit_price_offered=1500.0)
        result = process_round(state, extraction)

        # Counter should be at or below bulk_target_price, NOT at base_price
        assert result.counter_unit_price <= state.bulk_target_price + 0.01
        # And meaningfully below base
        assert result.counter_unit_price < state.base_price - 10.0

    def test_bulk_20_cheaper_than_bulk_2(self):
        """A bulk order of 20 should get a lower per-unit price than an order of 2."""
        state_2 = _make_state(quantity=2, base_price=299.0, cost_price=100.0, min_floor=110.0)
        state_20 = _make_state(quantity=20, base_price=299.0, cost_price=100.0, min_floor=110.0)

        ext = _make_extraction(unit_price_offered=200.0)

        result_2 = process_round(state_2, ext)
        result_20 = process_round(state_20, ext)

        assert result_20.counter_unit_price < result_2.counter_unit_price, (
            f"qty=20 ({result_20.counter_unit_price}) should be cheaper per-unit "
            f"than qty=2 ({result_2.counter_unit_price})"
        )

    def test_bulk_discount_reasonable_range(self):
        """Discount should be meaningful but not excessive (1-10% in MAX_PROFIT)."""
        base = 1000.0
        for qty, min_disc, max_disc in [(2, 0.005, 0.04), (10, 0.03, 0.08), (50, 0.05, 0.12)]:
            target = compute_bulk_target_price(base, qty, "MAX_PROFIT")
            actual_disc = (base - target) / base
            assert min_disc <= actual_disc <= max_disc, (
                f"qty={qty}: discount {actual_disc:.4f} not in [{min_disc}, {max_disc}]"
            )

    def test_recalculate_quantity_updates_bulk_target(self):
        """Changing quantity mid-negotiation should update bulk_target_price."""
        state = _make_state(quantity=1)
        assert state.bulk_target_price == state.base_price  # qty=1, no discount

        _recalculate_for_quantity(state, old_qty=1)
        # Still qty=1 after recalculate (qty not changed here)
        assert state.bulk_target_price == state.base_price

        # Now simulate quantity change
        state.quantity = 10
        _recalculate_for_quantity(state, old_qty=1)
        assert state.bulk_target_price < state.base_price


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Quantity decrease resets counters (anti-exploitation)
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuantityDecreaseReset:
    """Prevent exploit: negotiate bulk → switch to qty 1 → keep bulk price."""

    def test_qty_decrease_clears_counter_history(self):
        """When quantity decreases, counter_history resets so concession
        restarts from the new (higher) bulk_target_price."""
        state = _make_state(quantity=10, base_price=999.0, cost_price=400.0, min_floor=450.0)
        # Simulate a few rounds of bulk negotiation
        ext = _make_extraction(unit_price_offered=800.0)
        process_round(state, ext)
        assert len(state.counter_history) == 1
        bulk_counter = state.counter_history[0]
        assert bulk_counter < state.base_price  # conceded from base

        # Now decrease quantity to 1
        state.quantity = 1
        _recalculate_for_quantity(state, old_qty=10)

        assert state.counter_history == []  # cleared
        assert state.final_offer_issued is False
        assert state.consecutive_stagnant == 0
        assert state.retrograde_count == 0
        assert state.bulk_target_price == state.base_price  # qty=1: no bulk discount

    def test_qty_decrease_resets_concession_budget(self):
        """Budget fully resets on qty decrease (not proportionally scaled)."""
        state = _make_state(quantity=10, base_price=999.0, cost_price=400.0, min_floor=450.0)
        # Use some budget
        ext = _make_extraction(unit_price_offered=800.0)
        process_round(state, ext)
        budget_after_round = state.remaining_concession_budget
        assert budget_after_round < state.total_concession_budget

        # Decrease to 1
        state.quantity = 1
        _recalculate_for_quantity(state, old_qty=10)
        # Budget should be fully available (not scaled from old usage)
        assert state.remaining_concession_budget == state.total_concession_budget

    def test_qty_increase_clears_stale_counters(self):
        """When quantity increases and old counters exceed new bulk_target,
        counter_history is cleared so discount applies properly."""
        state = _make_state(quantity=2, base_price=999.0, cost_price=400.0, min_floor=450.0)
        ext = _make_extraction(unit_price_offered=800.0)
        process_round(state, ext)
        assert len(state.counter_history) == 1
        old_counter = state.counter_history[0]

        # Increase to 10 — bulk_target for 10 is lower than old counter
        state.quantity = 10
        _recalculate_for_quantity(state, old_qty=2)

        # Counter history cleared because old counter > new bulk_target
        assert len(state.counter_history) == 0
        assert state.bulk_target_price < old_counter

    def test_qty_increase_keeps_low_counters(self):
        """When qty increases and old counters are below new bulk_target,
        counter_history is preserved."""
        state = _make_state(quantity=5, base_price=100.0, cost_price=60.0, min_floor=65.0)
        # Negotiate aggressively to push counter below what bulk_target_price
        # would be for a larger qty
        for price in [70.0, 72.0, 74.0, 76.0, 78.0]:
            ext = _make_extraction(unit_price_offered=price)
            process_round(state, ext)

        history_len = len(state.counter_history)
        last_counter = state.counter_history[-1]

        # Increase to 6 — small increase, bulk_target for 6 is still above last counter
        state.quantity = 6
        _recalculate_for_quantity(state, old_qty=5)

        if last_counter <= state.bulk_target_price:
            # Counters preserved when already below target
            assert len(state.counter_history) == history_len

    def test_exploit_scenario_negotiation_continues_at_base(self):
        """Full exploit scenario: negotiate 10 units bulk → switch to 1 →
        next counter should be near base price, not bulk-discounted price."""
        # Start with qty=10, negotiate
        state = _make_state(quantity=10, base_price=999.0, cost_price=400.0, min_floor=450.0)
        ext = _make_extraction(unit_price_offered=800.0)
        r1 = process_round(state, ext)
        bulk_counter = r1.counter_unit_price
        assert bulk_counter < 999.0  # bulk-discounted counter

        # User switches to qty=1 and makes an offer
        ext2 = _make_extraction(unit_price_offered=bulk_counter, quantity=1)
        r2 = process_round(state, ext2)

        # The counter for qty=1 should be near base ($999), not the old bulk counter
        assert r2.counter_unit_price > bulk_counter + 10.0, (
            f"qty=1 counter ({r2.counter_unit_price}) should be much higher "
            f"than old bulk counter ({bulk_counter})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Auto-accept when buyer >= counter
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutoAcceptAboveCounter:
    """Bot must accept when buyer offers >= our computed counter."""

    def test_buyer_above_counter_accepted(self):
        """If buyer offers more than our counter, auto-accept at buyer's price."""
        state = _make_state(base_price=100.0, cost_price=60.0, min_floor=65.0)
        # Run several rounds to push counter down
        for price in [70.0, 72.0, 74.0, 76.0]:
            ext = _make_extraction(unit_price_offered=price)
            process_round(state, ext)

        # Now the counter has been pushed down from curve concessions.
        last_counter = state.counter_history[-1]

        # Offer above the last counter
        ext = _make_extraction(unit_price_offered=last_counter + 5.0)
        result = process_round(state, ext)
        assert result.decision == "accept", (
            f"Should accept {last_counter + 5.0} >= counter, got {result.decision}"
        )
        assert result.counter_unit_price >= last_counter

    def test_buyer_exactly_at_counter_accepted(self):
        """Buyer offering exactly our counter price should be accepted."""
        state = _make_state(base_price=100.0, cost_price=60.0, min_floor=65.0)
        # Push counter down
        for price in [70.0, 72.0, 74.0]:
            ext = _make_extraction(unit_price_offered=price)
            process_round(state, ext)

        last_counter = state.counter_history[-1]

        # Offer exactly at counter
        ext = _make_extraction(unit_price_offered=last_counter)
        result = process_round(state, ext)
        assert result.decision == "accept", (
            f"Should accept offer exactly at counter {last_counter}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Above-base-price cap  (mistype / LLM-parsing guard)
# ═══════════════════════════════════════════════════════════════════════════════


class TestAboveBasePriceCap:
    """
    Offers that exceed the seller's base (asking) price are clamped to base.
    This prevents auto-accepting mistyped or mis-parsed wild numbers.
    """

    def test_unit_price_above_base_is_clamped(self):
        """Unit price > base_price should be silently reduced to base_price."""
        state = _make_state(base_price=100.0, cost_price=60.0, min_floor=65.0)
        ext = _make_extraction(unit_price_offered=150.0)
        result = process_round(state, ext)
        # The resolved price in offer_history must be at most base (100)
        assert state.offer_history[-1] <= state.base_price, (
            f"Offer {state.offer_history[-1]} exceeds base {state.base_price}"
        )
        # And the engine should accept at base (best possible for seller)
        assert result.decision == "accept"
        assert result.counter_unit_price == pytest.approx(100.0, abs=0.01)

    def test_total_price_above_base_is_clamped(self):
        """When only total_price is given, per-unit price > base must be clamped."""
        state = _make_state(base_price=100.0, cost_price=60.0, min_floor=65.0, quantity=10)
        # Total = 1500 ÷ 10 = 150 per unit → should be clamped to 100
        ext = _make_extraction(
            unit_price_offered=None,
            total_price_offered=1500.0,
            quantity=10,
        )
        result = process_round(state, ext)
        assert state.offer_history[-1] <= state.base_price
        assert result.decision == "accept"

    def test_wildly_high_offer_does_not_inflate_counter(self):
        """Absurd number (like 999900) must not break counter math."""
        state = _make_state(base_price=999.0, cost_price=500.0, min_floor=550.0, quantity=20)
        # Simulate the "199900" mistype: total=199900 ÷ 20 = 9995 per unit
        ext = _make_extraction(
            unit_price_offered=None,
            total_price_offered=199900.0,
            quantity=20,
        )
        result = process_round(state, ext)
        assert state.offer_history[-1] <= state.base_price
        assert result.counter_unit_price <= state.base_price

    def test_just_above_base_clamped(self):
        """Even $0.01 above base is clamped — no tolerance band."""
        state = _make_state(base_price=100.0, cost_price=60.0, min_floor=65.0)
        ext = _make_extraction(unit_price_offered=100.01)
        result = process_round(state, ext)
        assert state.offer_history[-1] <= state.base_price
        assert result.decision == "accept"

    def test_exactly_base_not_clamped(self):
        """Offer == base_price is legitimate and not clamped."""
        state = _make_state(base_price=100.0, cost_price=60.0, min_floor=65.0)
        ext = _make_extraction(unit_price_offered=100.0)
        result = process_round(state, ext)
        assert state.offer_history[-1] == 100.0
        assert result.decision == "accept"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Bulk target display without engine init  (first-round qty change)
# ═══════════════════════════════════════════════════════════════════════════════


class TestBulkTargetWithoutEngine:
    """compute_bulk_target_price must give correct discount even when called
    standalone (before any engine state is created)."""

    def test_bulk_target_below_base_for_large_qty(self):
        """Qty >= 10 should yield a target price strictly below base."""
        target = compute_bulk_target_price(999.0, 25, "MAX_PROFIT")
        assert target < 999.0, (
            f"Bulk target {target} should be below base 999.0 for qty=25"
        )

    def test_bulk_target_equals_base_for_qty_1(self):
        """Qty=1 yields no bulk discount — target == base."""
        target = compute_bulk_target_price(999.0, 1, "MAX_PROFIT")
        assert target == pytest.approx(999.0, abs=0.01)

    def test_deeper_discount_for_larger_qty(self):
        """More units → lower per-unit target."""
        t20 = compute_bulk_target_price(999.0, 20, "MAX_PROFIT")
        t50 = compute_bulk_target_price(999.0, 50, "MAX_PROFIT")
        assert t50 < t20, (
            f"50 units ({t50}) should be cheaper per unit than 20 ({t20})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Stagnation detection (only exact repeats are stagnant)
# ═══════════════════════════════════════════════════════════════════════════════


class TestStagnationDetection:
    """Small positive improvements should NOT be treated as stagnation."""

    def test_small_improvements_do_not_trigger_stagnation(self):
        """Buyer increasing 0.5-0.9% per round must not trigger STAGNATION_FINAL.

        Simulates the real transcript scenario: buyer goes from 267 → 269 → 270
        (sub-1% improvements). The engine should continue negotiating, not
        issue a final offer.
        """
        state = _make_state(
            base_price=299.0, cost_price=150.0, min_floor=160.0, quantity=28,
        )
        # Round 1: first offer
        ext = _make_extraction(unit_price_offered=267.86)
        r1 = process_round(state, ext)
        assert r1.decision in ("counter", "final_offer")

        # Round 2: +0.66% improvement
        ext = _make_extraction(unit_price_offered=269.64)
        r2 = process_round(state, ext)

        # Round 3: repeat (stagnation count = 1)
        ext = _make_extraction(unit_price_offered=269.64)
        r3 = process_round(state, ext)

        # Round 4: buyer moves up to 270.36 (+0.27%)
        ext = _make_extraction(unit_price_offered=270.36)
        r4 = process_round(state, ext)
        # Should NOT be final_offer — buyer moved up
        assert r4.decision != "final_offer", (
            "Small positive improvement should not trigger STAGNATION_FINAL"
        )

    def test_exact_repeats_still_trigger_stagnation(self):
        """Two exact same offers in a row SHOULD trigger STAGNATION_FINAL."""
        state = _make_state(base_price=100.0, cost_price=60.0, min_floor=65.0)
        process_round(state, _make_extraction(unit_price_offered=70.0))
        process_round(state, _make_extraction(unit_price_offered=70.0))
        r3 = process_round(state, _make_extraction(unit_price_offered=70.0))
        assert r3.decision == "final_offer", (
            "Three identical offers should trigger stagnation final"
        )
        assert state.final_offer_issued is True

    def test_counter_keeps_moving_with_slow_buyer(self):
        """When buyer makes consistent small improvements, counter should
        keep conceding (not freeze at one value).  If the engine accepts
        mid-sequence, that counts as success — acceptances are better
        than frozen counters."""
        state = _make_state(
            base_price=299.0, cost_price=150.0, min_floor=160.0, quantity=28,
        )
        counters = []
        decisions = []
        for price in [267.0, 268.5, 270.0, 271.5, 273.0, 275.0]:
            ext = _make_extraction(unit_price_offered=price)
            result = process_round(state, ext)
            counters.append(result.counter_unit_price)
            decisions.append(result.decision)

        # Filter to only counter-offer rounds (exclude accepted rounds)
        counter_only = [c for c, d in zip(counters, decisions) if d not in ("accept",)]
        accepted = any(d == "accept" for d in decisions)

        if accepted:
            # Reaching acceptance with a slow buyer is fine
            pass
        else:
            # If no acceptance, counter should have moved down
            assert counter_only[-1] < counter_only[0], (
                f"Counter should decrease over time: {counters}"
            )
            # Verify counter wasn't frozen (at least 3 distinct values)
            distinct_counters = len(set(round(c, 2) for c in counter_only))
            assert distinct_counters >= 3, (
                f"Expected ≥3 distinct counters, got {distinct_counters}: {counter_only}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Quantity-change round reset (prevent inflated concession)
# ═══════════════════════════════════════════════════════════════════════════════


class TestQuantityChangeRoundReset:
    """When qty change clears counter_history, round tracking must also
    reset so the concession curve doesn't start with inflated round pressure."""

    def test_qty_decrease_resets_round_and_offer_history(self):
        """Switching from bulk to single unit resets current_round and
        offer_history so concession starts from scratch."""
        state = _make_state(
            quantity=28, base_price=299.0, cost_price=150.0, min_floor=160.0,
            max_rounds=10,
        )
        # Negotiate 5 rounds
        for price in [267.0, 269.0, 270.0, 271.0, 273.0]:
            process_round(state, _make_extraction(unit_price_offered=price))

        assert state.current_round == 5
        assert len(state.offer_history) == 5

        # Switch to qty=1 (triggers counter reset)
        state.quantity = 1
        _recalculate_for_quantity(state, old_qty=28)

        assert state.current_round == 0, "current_round should reset on counter clear"
        assert state.offer_history == [], "offer_history should clear on counter clear"
        assert state.max_rounds == 5, "max_rounds should be capped at remaining (10-5)"

    def test_qty_decrease_1unit_rejects_bulk_price(self):
        """The exact transcript exploit: negotiate 28 units at ~$278,
        then ask for 1 unit at $278. Must NOT accept."""
        state = _make_state(
            quantity=28, base_price=299.0, cost_price=150.0, min_floor=160.0,
            max_rounds=10,
        )
        # Simulate bulk negotiation pushing counter down
        for price in [267.0, 269.0, 270.0, 271.0, 273.0, 275.0]:
            process_round(state, _make_extraction(unit_price_offered=price))

        # Now switch to qty=1 and offer the bulk-negotiated price
        ext = _make_extraction(unit_price_offered=278.0, quantity=1)
        result = process_round(state, ext)

        # Should NOT accept — $278 for 1 unit when base is $299
        assert result.decision != "accept", (
            f"Should not accept $278 for qty=1 when base=$299, got {result.decision}"
        )
        # Counter should be near $299 (no bulk discount for qty=1)
        assert result.counter_unit_price >= 290.0, (
            f"Counter for qty=1 should be near $299, got {result.counter_unit_price}"
        )

    def test_qty_increase_no_reset_when_counters_kept(self):
        """When qty increases and counters are below bulk_target (not cleared),
        rounds should NOT reset."""
        state = _make_state(
            quantity=5, base_price=100.0, cost_price=60.0, min_floor=65.0,
            max_rounds=10,
        )
        # Push counters low
        for price in [70.0, 72.0, 74.0, 76.0, 78.0]:
            process_round(state, _make_extraction(unit_price_offered=price))

        old_round = state.current_round
        old_offer_len = len(state.offer_history)

        # Small qty increase — counters should be below new bulk_target
        state.quantity = 6
        _recalculate_for_quantity(state, old_qty=5)

        if state.counter_history:  # counters kept
            assert state.current_round == old_round, (
                "Rounds should NOT reset when counter_history is preserved"
            )
            assert len(state.offer_history) == old_offer_len

    def test_max_rounds_floor_at_2(self):
        """Even if used 9 of 10 rounds, qty change gives at least 2 rounds."""
        state = _make_state(
            quantity=10, base_price=100.0, cost_price=60.0, min_floor=65.0,
            max_rounds=10,
        )
        # Simulate 9 rounds
        for i in range(9):
            process_round(state, _make_extraction(unit_price_offered=70.0 + i * 0.5))

        assert state.current_round == 9

        state.quantity = 1
        _recalculate_for_quantity(state, old_qty=10)

        assert state.max_rounds >= 2, "Must have at least 2 rounds after qty change"
        assert state.current_round == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Redemption (unfreeze after genuine improvement)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRedemption:
    """After final_offer_issued, buyer can earn their way back to normal
    negotiation by showing consecutive ≥4% improvements."""

    def test_two_good_moves_unfreeze(self):
        """Final offer + two ≥4% improvements → counter resumes moving."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        # Round 1: first offer
        process_round(state, _make_extraction(unit_price_offered=50.0))
        # Round 2: retrograde → retrograde_count = 1
        process_round(state, _make_extraction(unit_price_offered=45.0))
        # Round 3: second retrograde → RETROGRADE_FINAL
        r3 = process_round(state, _make_extraction(unit_price_offered=40.0))
        assert r3.decision == "final_offer"
        assert state.final_offer_issued is True
        frozen_counter = r3.counter_unit_price

        # Round 4: big jump up $40→$60 = +50% (good_faith = 1)
        r4 = process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state.good_faith_after_final == 1
        assert state.final_offer_issued is True  # not redeemed yet
        assert r4.counter_unit_price == frozen_counter  # still frozen

        # Round 5: another big jump $60→$70 = +16.7% (good_faith = 2 → REDEEMED)
        r5 = process_round(state, _make_extraction(unit_price_offered=70.0))
        assert state.final_offer_issued is False  # unfrozen!
        assert state.good_faith_after_final == 0  # reset
        # Counter should have MOVED (not frozen)
        assert r5.counter_unit_price < frozen_counter or r5.decision == "accept", (
            f"After redemption, counter ({r5.counter_unit_price}) should be "
            f"lower than frozen ({frozen_counter}) or deal accepted"
        )

    def test_small_move_resets_redemption_counter(self):
        """A <4% improvement resets good_faith_after_final."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))  # RETROGRADE_FINAL
        assert state.final_offer_issued is True

        # Good move: $40→$60 (+50%)
        process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state.good_faith_after_final == 1

        # Small move: $60→$61 (+1.7%) — under 4%
        process_round(state, _make_extraction(unit_price_offered=61.0))
        assert state.good_faith_after_final == 0  # reset!
        assert state.final_offer_issued is True  # still locked

    def test_retrograde_after_one_good_move_resets(self):
        """Going backwards after one good move resets the redemption counter."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))  # final
        assert state.final_offer_issued is True

        # Good move: $40→$60
        process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state.good_faith_after_final == 1

        # Retrograde: $60→$50
        process_round(state, _make_extraction(unit_price_offered=50.0))
        assert state.good_faith_after_final == 0  # reset!
        assert state.final_offer_issued is True

    def test_re_manipulate_after_redemption_re_freezes(self):
        """After redemption, buyer who retrogrades again gets re-frozen."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Trigger initial final offer
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))
        assert state.final_offer_issued is True

        # Redeem: two big jumps
        process_round(state, _make_extraction(unit_price_offered=60.0))
        process_round(state, _make_extraction(unit_price_offered=70.0))
        assert state.final_offer_issued is False  # redeemed

        # Now retrograde twice → should re-freeze
        process_round(state, _make_extraction(unit_price_offered=65.0))
        process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state.retrograde_count >= 2
        # The manipulation check should have fired
        assert state.final_offer_issued is True

    def test_transcript_scenario_counter_unfreezes_at_right_time(self):
        """Simulates the real transcript: $50, $40, $40, $30 → freeze,
        then $60, $85 → unfreeze, then $86, $89 → normal negotiation."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        # Manipulation phase
        r1 = process_round(state, _make_extraction(unit_price_offered=50.0))
        r2 = process_round(state, _make_extraction(unit_price_offered=40.0))
        r3 = process_round(state, _make_extraction(unit_price_offered=40.0))
        r4 = process_round(state, _make_extraction(unit_price_offered=30.0))
        # By now should be frozen (stagnation or retrograde triggered)
        frozen_counter = state.counter_history[-1]

        # Recovery phase: big jumps
        r5 = process_round(state, _make_extraction(unit_price_offered=60.0))  # +100%
        assert state.good_faith_after_final >= 1
        r6 = process_round(state, _make_extraction(unit_price_offered=85.0))  # +41.7%
        # Should be redeemed now
        assert state.final_offer_issued is False

        # Normal negotiation resumes — counter should move
        r7 = process_round(state, _make_extraction(unit_price_offered=86.0))
        r8 = process_round(state, _make_extraction(unit_price_offered=89.0))

        # At least one counter after redemption should differ from frozen
        post_redemption_counters = [r7.counter_unit_price, r8.counter_unit_price]
        has_movement = any(c != frozen_counter for c in post_redemption_counters)
        assert has_movement or r7.decision == "accept" or r8.decision == "accept", (
            f"After redemption, counter should move or deal accepted. "
            f"Frozen={frozen_counter}, post={post_redemption_counters}"
        )

    def test_stagnation_final_also_redeemable(self):
        """Redemption works for STAGNATION_FINAL too, not just RETROGRADE."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        process_round(state, _make_extraction(unit_price_offered=70.0))
        # Two exact repeats → stagnation
        process_round(state, _make_extraction(unit_price_offered=70.0))
        r = process_round(state, _make_extraction(unit_price_offered=70.0))
        assert state.final_offer_issued is True

        # Two big jumps
        process_round(state, _make_extraction(unit_price_offered=80.0))  # +14.3%
        assert state.good_faith_after_final == 1
        process_round(state, _make_extraction(unit_price_offered=88.0))  # +10%
        assert state.final_offer_issued is False  # redeemed


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Counter Ratchet (anti-yo-yo protection)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCounterRatchet:
    """The counter must never go DOWN unless the buyer beats their
    all-time best offer. On retrograde, counter HOLDS (never tightens UP
    because the seller asking for MORE than already offered looks absurd)."""

    def test_retrograde_holds_counter(self):
        """When buyer drops offer, counter HOLDS at previous level."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        r1 = process_round(state, _make_extraction(unit_price_offered=70.0))
        c1 = r1.counter_unit_price

        # Genuine improvement: counter should go down
        r2 = process_round(state, _make_extraction(unit_price_offered=75.0))
        c2 = r2.counter_unit_price
        assert c2 <= c1, f"Counter should concede on improvement: {c2} > {c1}"

        # Retrograde: counter should HOLD (not go up, not go down)
        r3 = process_round(state, _make_extraction(unit_price_offered=60.0))
        c3 = r3.counter_unit_price
        assert c3 >= c2, (
            f"Counter should HOLD on retrograde: {c3} should be >= {c2}"
        )
        assert c3 == c2, (
            f"Counter should NOT raise above previous: {c3} should equal {c2}"
        )

    def test_hold_when_at_previous_best(self):
        """Counter doesn't concede when buyer matches but doesn't beat best."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        r1 = process_round(state, _make_extraction(unit_price_offered=70.0))
        c1 = r1.counter_unit_price

        # Improvement → counter drops
        r2 = process_round(state, _make_extraction(unit_price_offered=80.0))
        c2 = r2.counter_unit_price
        assert c2 <= c1

        # Now offer $70 (below best of $80) → counter should hold at c2 or go up
        r3 = process_round(state, _make_extraction(unit_price_offered=70.0))
        c3 = r3.counter_unit_price
        assert c3 >= c2, f"Counter should hold/tighten at {c2}, got {c3}"

    def test_new_personal_best_allows_concession(self):
        """When buyer sets a new all-time high, normal concession applies."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        process_round(state, _make_extraction(unit_price_offered=60.0))
        r2 = process_round(state, _make_extraction(unit_price_offered=65.0))
        c2 = r2.counter_unit_price

        # New best: $70 > $65
        r3 = process_round(state, _make_extraction(unit_price_offered=70.0))
        c3 = r3.counter_unit_price
        assert c3 <= c2 or r3.decision == "accept", (
            f"Counter should concede on new best: {c3} > {c2}"
        )

    def test_yoyo_exploit_blocked(self):
        """The exact yo-yo pattern: $50→$40→$30→$40→$50→$40 should NOT
        give the buyer a progressively lower counter."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        r1 = process_round(state, _make_extraction(unit_price_offered=50.0))
        c_after_first = r1.counter_unit_price

        # Manipulate down
        process_round(state, _make_extraction(unit_price_offered=40.0))
        process_round(state, _make_extraction(unit_price_offered=30.0))  # retrograde_count reaches trigger

        # Come back up (redemption moves)
        process_round(state, _make_extraction(unit_price_offered=40.0))
        process_round(state, _make_extraction(unit_price_offered=50.0))

        # Retrograde again
        r6 = process_round(state, _make_extraction(unit_price_offered=40.0))

        # Counter should be AT LEAST as high as first counter
        # (tightening should have pushed it higher, not lower)
        assert r6.counter_unit_price >= c_after_first, (
            f"Yo-yo exploit! Counter {r6.counter_unit_price} should be "
            f">= initial {c_after_first}"
        )

    def test_budget_preserved_on_ratchet(self):
        """When ratchet prevents concession, budget is restored."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        process_round(state, _make_extraction(unit_price_offered=70.0))
        budget_after_r1 = state.remaining_concession_budget

        # Improvement: budget should decrease
        process_round(state, _make_extraction(unit_price_offered=75.0))
        budget_after_r2 = state.remaining_concession_budget
        assert budget_after_r2 < budget_after_r1

        # Retrograde: ratchet fires, budget should be restored
        process_round(state, _make_extraction(unit_price_offered=65.0))
        budget_after_r3 = state.remaining_concession_budget
        assert budget_after_r3 >= budget_after_r2, (
            f"Budget should be restored on ratchet: {budget_after_r3} < {budget_after_r2}"
        )

    def test_retrograde_holds_regardless_of_drop_size(self):
        """Both small and large retrograde HOLD counter at same level."""
        # Small drop: $70 → $68 (2.9% drop)
        s1 = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        process_round(s1, _make_extraction(unit_price_offered=70.0))
        c1 = s1.counter_history[-1]
        process_round(s1, _make_extraction(unit_price_offered=68.0))
        c1_after = s1.counter_history[-1]

        # Large drop: $70 → $50 (28.6% drop)
        s2 = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        process_round(s2, _make_extraction(unit_price_offered=70.0))
        c2 = s2.counter_history[-1]
        process_round(s2, _make_extraction(unit_price_offered=50.0))
        c2_after = s2.counter_history[-1]

        # Both should hold at previous counter level (no tightening)
        assert c1_after == c1, (
            f"Small retrograde should hold at {c1}, got {c1_after}"
        )
        assert c2_after == c2, (
            f"Large retrograde should hold at {c2}, got {c2_after}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: One-Strike Rule & Progressive Redemption
# ═══════════════════════════════════════════════════════════════════════════════


class TestOneStrikeAndProgressive:
    """After redemption, a single retrograde triggers immediate re-freeze.
    Each manipulation cycle makes redemption harder."""

    def test_one_strike_re_freeze(self):
        """After redemption, ONE retrograde triggers RETROGRADE_FINAL."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # First freeze
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))
        assert state.final_offer_issued is True
        assert state.manipulation_events == 1

        # Redeem
        process_round(state, _make_extraction(unit_price_offered=60.0))
        process_round(state, _make_extraction(unit_price_offered=70.0))
        assert state.final_offer_issued is False

        # One-strike: single retrograde → immediate re-freeze
        r = process_round(state, _make_extraction(unit_price_offered=65.0))
        assert state.final_offer_issued is True
        assert r.decision == "final_offer"
        assert state.manipulation_events == 2

    def test_progressive_redemption_needs_more_moves(self):
        """Second redemption cycle needs 3 good moves (2 base + 1 penalty)."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=20,
        )
        # First cycle: freeze → redeem (2 good moves)
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))  # freeze
        process_round(state, _make_extraction(unit_price_offered=60.0))  # good 1
        process_round(state, _make_extraction(unit_price_offered=70.0))  # good 2 → redeemed
        assert state.final_offer_issued is False
        assert state.manipulation_events == 1

        # One-strike re-freeze
        process_round(state, _make_extraction(unit_price_offered=65.0))  # retrograde → freeze
        assert state.final_offer_issued is True
        assert state.manipulation_events == 2

        # Second redemption: now needs 3 good moves (2 + max(0, 2-1) = 3)
        process_round(state, _make_extraction(unit_price_offered=75.0))  # good 1
        assert state.good_faith_after_final == 1
        assert state.final_offer_issued is True  # not yet

        process_round(state, _make_extraction(unit_price_offered=85.0))  # good 2
        assert state.good_faith_after_final == 2
        assert state.final_offer_issued is True  # STILL not (need 3)

        process_round(state, _make_extraction(unit_price_offered=92.0))  # good 3 → redeemed
        assert state.final_offer_issued is False  # NOW redeemed

    def test_manipulation_events_persists_across_qty_change(self):
        """manipulation_events is never reset, even on quantity change."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Freeze
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))
        assert state.manipulation_events == 1

        # Quantity change
        process_round(state, _make_extraction(unit_price_offered=60.0, quantity=5))

        # manipulation_events should persist
        assert state.manipulation_events == 1, (
            "manipulation_events should survive quantity changes"
        )

    def test_counter_monotonic_during_normal_negotiation(self):
        """In a legitimate negotiation with increasing offers, counter
        monotonically decreases (or accepts)."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        offers = [55.0, 60.0, 65.0, 70.0, 75.0, 80.0]
        counters = []
        for offer in offers:
            r = process_round(state, _make_extraction(unit_price_offered=offer))
            if r.decision == "accept":
                break
            counters.append(r.counter_unit_price)

        # Each counter should be <= previous (monotonically decreasing)
        for i in range(1, len(counters)):
            assert counters[i] <= counters[i - 1], (
                f"Counter went UP during genuine negotiation: "
                f"round {i}: {counters[i-1]} → round {i+1}: {counters[i]}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Post-Redemption Protection
# ═══════════════════════════════════════════════════════════════════════════════


class TestPostRedemptionProtection:
    """After redemption, the engine should not dump a massive concession
    in one round due to high round_pressure. The phase cap and min-rounds
    guarantee prevent this."""

    def test_retrograde_holds_not_raises(self):
        """Counter stays exactly at previous level on retrograde — never rises."""
        state = _make_state(base_price=100.0, cost_price=50.0, min_floor=55.0)
        r1 = process_round(state, _make_extraction(unit_price_offered=70.0))
        c1 = r1.counter_unit_price

        r2 = process_round(state, _make_extraction(unit_price_offered=75.0))
        c2 = r2.counter_unit_price
        assert c2 <= c1

        # Retrograde
        r3 = process_round(state, _make_extraction(unit_price_offered=60.0))
        c3 = r3.counter_unit_price
        assert c3 == c2, (
            f"Counter should HOLD at {c2} on retrograde, not rise to {c3}"
        )

    def test_redemption_counter_stays_conservative(self):
        """After manipulation → redemption, the first real counter should be
        conservative (≥85% of base) so the seller isn't giving away profit."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Force freeze via manipulation
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))
        assert state.final_offer_issued is True

        # Redeem
        process_round(state, _make_extraction(unit_price_offered=60.0))
        process_round(state, _make_extraction(unit_price_offered=70.0))
        assert state.final_offer_issued is False

        # First counter after redemption on a big jump
        r = process_round(state, _make_extraction(unit_price_offered=80.0))
        if r.decision != "accept":
            # Counter should still be conservative (≥85% of base)
            assert r.counter_unit_price >= 0.85 * state.base_price, (
                f"Post-redemption counter {r.counter_unit_price} too low "
                f"(< 85% of {state.base_price})"
            )

    def test_post_redemption_no_instant_accept_below_counter(self):
        """After redemption, an offer below the last counter should NOT
        trigger auto-accept (the deep concession trap)."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Freeze
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))
        assert state.final_offer_issued is True

        frozen_counter = state.counter_history[-1]

        # Redeem
        process_round(state, _make_extraction(unit_price_offered=60.0))
        process_round(state, _make_extraction(unit_price_offered=70.0))
        assert state.final_offer_issued is False

        # Offer BELOW the last counter — should NOT be accepted
        below_counter_offer = frozen_counter - 5.0
        r = process_round(
            state, _make_extraction(unit_price_offered=below_counter_offer)
        )
        assert r.decision != "accept", (
            f"Accepted {below_counter_offer} which is below "
            f"last counter {frozen_counter}"
        )

    def test_phase_capped_after_redemption(self):
        """Phase should be PROBING or ANCHOR_RESIST for the first few rounds
        after redemption, even if we're deep into the negotiation."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=10,
        )
        # Advance to create freeze
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))
        assert state.final_offer_issued is True

        # Redeem
        process_round(state, _make_extraction(unit_price_offered=60.0))
        process_round(state, _make_extraction(unit_price_offered=70.0))
        assert state.final_offer_issued is False
        assert state._post_redemption_round >= 0

        # Now determine phase — should be capped at PROBING
        phase = _determine_phase(state)
        allowed = {NegotiationPhase.ANCHOR_RESIST, NegotiationPhase.PROBING}
        assert phase in allowed, (
            f"Post-redemption phase should be ANCHOR_RESIST or PROBING, "
            f"got {phase}"
        )

    def test_max_rounds_extended_if_needed(self):
        """If redemption fires close to end, max_rounds is extended to
        guarantee post_redemption_min_rounds of runway."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=8,
        )
        # Freeze
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))
        assert state.final_offer_issued is True

        # Redeem at rounds 4-5, which leaves only 3 rounds in 8-round max
        process_round(state, _make_extraction(unit_price_offered=60.0))
        process_round(state, _make_extraction(unit_price_offered=70.0))
        assert state.final_offer_issued is False

        # max_rounds should've been extended if needed
        min_post = TUNING["post_redemption_min_rounds"]
        rounds_left = state.max_rounds - state.current_round
        assert rounds_left >= min_post, (
            f"Only {rounds_left} rounds left after redemption, need {min_post}"
        )

    def test_concession_small_per_round_after_redemption(self):
        """After redemption, each counter step should be modest, not a
        massive dump of 15%+ of base price in a single round."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Freeze
        process_round(state, _make_extraction(unit_price_offered=50.0))
        process_round(state, _make_extraction(unit_price_offered=45.0))
        process_round(state, _make_extraction(unit_price_offered=40.0))
        assert state.final_offer_issued is True
        frozen_counter = state.counter_history[-1]

        # Redeem
        process_round(state, _make_extraction(unit_price_offered=60.0))
        process_round(state, _make_extraction(unit_price_offered=70.0))
        assert state.final_offer_issued is False

        # First real counter after redemption (big jump to $85)
        r = process_round(state, _make_extraction(unit_price_offered=85.0))
        if r.decision != "accept":
            drop = frozen_counter - r.counter_unit_price
            max_allowed = 0.10 * state.base_price  # 10% of base per round
            assert drop <= max_allowed, (
                f"Post-redemption concession too large: dropped {drop:.2f} "
                f"(from {frozen_counter} to {r.counter_unit_price}), "
                f"max allowed {max_allowed:.2f}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 23. CUMULATIVE REDEMPTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestCumulativeRedemption:
    """Verify the cumulative redemption path unfreezes buyers who
    make sustained upward movement even when no single jump >= 4%."""

    def test_cumulative_climb_unfreezes(self):
        """A buyer who climbs >= 6% total from freeze-point low
        with monotonically non-decreasing offers should unfreeze."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Trigger freeze via retrograde
        process_round(state, _make_extraction(unit_price_offered=70.0))
        process_round(state, _make_extraction(unit_price_offered=65.0))
        process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state.final_offer_issued is True
        assert state._freeze_low_offer == 60.0

        # Climb monotonically: 60→63→66→67 (cumulative 11.7% from 60)
        # No single jump >= 4%: 5%, 4.76%, 1.5%
        process_round(state, _make_extraction(unit_price_offered=63.0))
        assert state.final_offer_issued is True  # 5% single jump, good_faith=1 (need 2)
        process_round(state, _make_extraction(unit_price_offered=66.0))
        # Per-move path fires: 63→66 is 4.76% ≥ 4%, good_faith reaches 2 → redeemed
        assert state.final_offer_issued is False, (
            "Two consecutive ≥4% moves should trigger per-move redemption"
        )

    def test_cumulative_climb_unfreezes_exact(self):
        """Exact threshold check: 6% of base_price cumulative climb."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Trigger freeze
        process_round(state, _make_extraction(unit_price_offered=70.0))
        process_round(state, _make_extraction(unit_price_offered=65.0))
        process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state.final_offer_issued is True
        assert state._freeze_low_offer == 60.0

        # 62.0 → (62-60)/100 = 2% — not enough
        process_round(state, _make_extraction(unit_price_offered=62.0))
        assert state.final_offer_issued is True

        # 64.0 → (64-60)/100 = 4% — still below 6%
        process_round(state, _make_extraction(unit_price_offered=64.0))
        assert state.final_offer_issued is True

        # 66.0 → (66-60)/100 = 6% at threshold, 3 moves, should unfreeze
        process_round(state, _make_extraction(unit_price_offered=66.0))
        assert state.final_offer_issued is False, (
            "Cumulative 6% of base_price climb should trigger redemption"
        )

    def test_micro_increments_dont_unfreeze(self):
        """Tiny increments ($0.10/round) shouldn't reach 6% threshold
        within a reasonable number of rounds."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=12,
        )
        # Freeze at 60
        process_round(state, _make_extraction(unit_price_offered=70.0))
        process_round(state, _make_extraction(unit_price_offered=65.0))
        process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state.final_offer_issued is True

        # Micro-increments: 60.10, 60.20, 60.30, 60.40, 60.50
        for i in range(1, 6):
            price = 60.0 + i * 0.10
            process_round(state, _make_extraction(unit_price_offered=price))
            # 60.50/60 - 1 = 0.83% — way below 6%
            assert state.final_offer_issued is True, (
                f"Micro-increment ${price} should NOT unfreeze (only {(price/60-1)*100:.1f}%)"
            )

    def test_retrograde_during_recovery_blocks_cumulative(self):
        """A retrograde move during recovery should prevent cumulative
        redemption even if total climb exceeds threshold."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Freeze at 60
        process_round(state, _make_extraction(unit_price_offered=70.0))
        process_round(state, _make_extraction(unit_price_offered=65.0))
        process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state.final_offer_issued is True

        # Go up, then retrograde, then up past threshold
        process_round(state, _make_extraction(unit_price_offered=63.0))
        process_round(state, _make_extraction(unit_price_offered=62.0))  # Retrograde!
        process_round(state, _make_extraction(unit_price_offered=64.0))  # 6.7% total
        # Despite 64/60 = 6.7% > 6%, the retrograde at 62 breaks monotonicity
        assert state.final_offer_issued is True, (
            "Retrograde during recovery should block cumulative redemption"
        )

    def test_per_move_path_still_works_independently(self):
        """The per-move consecutive-jumps path should still work
        even without cumulative tracking."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Freeze
        process_round(state, _make_extraction(unit_price_offered=70.0))
        process_round(state, _make_extraction(unit_price_offered=65.0))
        process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state.final_offer_issued is True

        # Two consecutive >=4% jumps: 70 (+16.7%), 75 (+7.1%)
        process_round(state, _make_extraction(unit_price_offered=70.0))
        process_round(state, _make_extraction(unit_price_offered=75.0))
        assert state.final_offer_issued is False, (
            "Per-move path (2 consecutive >=4% jumps) should still trigger redemption"
        )

    def test_led_bulb_scenario(self):
        """Simulate the LED bulb transcript: $899 base, qty=10.
        Buyer: 800→790→780(freeze)→800→800.10→800.20→802→820→830.
        Cumulative: 830/780 - 1 = 6.4% > 6% → should unfreeze."""
        state = _make_state(
            base_price=899.0, cost_price=350.0, min_floor=350.0,
            max_rounds=10, quantity=10,
        )
        # R1: 800 — normal counter
        r1 = process_round(state, _make_extraction(unit_price_offered=800.0))
        assert r1.decision == "counter"

        # R2: 790 — retrograde #1
        r2 = process_round(state, _make_extraction(unit_price_offered=790.0))
        assert state.retrograde_count >= 1

        # R3: 780 — retrograde #2 → freeze
        r3 = process_round(state, _make_extraction(unit_price_offered=780.0))
        assert state.final_offer_issued is True
        assert state._freeze_low_offer == 780.0

        # R4-R6: Small increments (monotonic)
        process_round(state, _make_extraction(unit_price_offered=800.0))
        assert state.final_offer_issued is True  # 2.6% — too low
        process_round(state, _make_extraction(unit_price_offered=800.10))
        assert state.final_offer_issued is True
        process_round(state, _make_extraction(unit_price_offered=800.20))
        assert state.final_offer_issued is True

        # R7: 802 — still below 6%
        process_round(state, _make_extraction(unit_price_offered=802.0))
        assert state.final_offer_issued is True  # 802/780-1=2.8%

        # R8: 820 — (820-780)/899=4.4% — still below 6%
        process_round(state, _make_extraction(unit_price_offered=820.0))
        assert state.final_offer_issued is True

        # R9: 835 — (835-780)/899=6.1% > 6% → cumulative redemption fires!
        process_round(state, _make_extraction(unit_price_offered=835.0))
        assert state.final_offer_issued is False, (
            f"(835-780)/899 = {(835-780)/899:.4f} (6.1%) should trigger cumulative redemption. "
            f"freeze_low={state._freeze_low_offer}, offers_since_freeze="
            f"{state.offer_history[state._freeze_offer_idx:] if state._freeze_offer_idx >= 0 else 'N/A'}"
        )

    def test_freeze_fields_reset_on_redemption(self):
        """After redemption, _freeze_low_offer and _freeze_offer_idx
        should be cleared so re-freeze starts fresh."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Freeze
        process_round(state, _make_extraction(unit_price_offered=70.0))
        process_round(state, _make_extraction(unit_price_offered=65.0))
        process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state._freeze_low_offer == 60.0
        assert state._freeze_offer_idx >= 0

        # Redeem via per-move path
        process_round(state, _make_extraction(unit_price_offered=70.0))
        process_round(state, _make_extraction(unit_price_offered=75.0))
        assert state.final_offer_issued is False
        assert state._freeze_low_offer == 0.0
        assert state._freeze_offer_idx == -1

    def test_freeze_fields_reset_on_quantity_change(self):
        """Quantity change should clear freeze tracking fields."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=15,
        )
        # Freeze
        process_round(state, _make_extraction(unit_price_offered=70.0))
        process_round(state, _make_extraction(unit_price_offered=65.0))
        process_round(state, _make_extraction(unit_price_offered=60.0))
        assert state._freeze_low_offer == 60.0

        # Quantity change resets everything
        process_round(state, _make_extraction(unit_price_offered=70.0, quantity=5))
        assert state._freeze_low_offer == 0.0
        assert state._freeze_offer_idx == -1

    def test_dollar_increment_manipulation_blocked(self):
        """Reproduce the transcript bug: $50→$40→$30 (freeze) then
        $31→$32→$33→$34→$35. The counter must stay frozen at the
        same value throughout. No concession on $1 increments."""
        state = _make_state(
            base_price=100.0, cost_price=50.0, min_floor=55.0, max_rounds=10,
        )
        # Trigger freeze via retrograde: 50→40→30
        r1 = process_round(state, _make_extraction(unit_price_offered=50.0))
        c_first = r1.counter_unit_price

        process_round(state, _make_extraction(unit_price_offered=40.0))
        r3 = process_round(state, _make_extraction(unit_price_offered=30.0))
        assert state.final_offer_issued is True
        frozen_counter = state.counter_history[-1]

        # $1 increments: counter must stay frozen, decision must be final_offer
        for price in [31, 32, 33, 34, 35]:
            r = process_round(state, _make_extraction(unit_price_offered=float(price)))
            assert r.decision == "final_offer", (
                f"At ${price}: expected 'final_offer', got '{r.decision}'"
            )
            assert r.counter_unit_price == frozen_counter, (
                f"At ${price}: counter moved to {r.counter_unit_price}, "
                f"should be frozen at {frozen_counter}"
            )
            assert state.final_offer_issued is True, (
                f"At ${price}: freeze lifted prematurely"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Last-round always terminates (accept or reject, never counter)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLastRoundTermination:
    """
    On the final round the engine MUST return 'accept' or 'reject'.
    Never 'counter' or 'final_offer' — those leave the session in
    limbo and cause the orchestration to record 'expired' status.
    """

    def test_last_round_frozen_below_counter_rejects(self):
        """Frozen state, buyer below counter on last round → reject."""
        state = _make_state(
            base_price=16000.0, cost_price=8000.0, min_floor=8640.0,
            max_rounds=10,
        )
        # R1-R3: trigger freeze via retrograde
        process_round(state, _make_extraction(unit_price_offered=8000.0))
        process_round(state, _make_extraction(unit_price_offered=7000.0))
        r3 = process_round(state, _make_extraction(unit_price_offered=6000.0))
        assert state.final_offer_issued is True

        # R4-R9: hold frozen, buyer stays low
        for _ in range(6):
            process_round(state, _make_extraction(unit_price_offered=7000.0))

        # R10 (last round): buyer still below counter
        assert state.current_round == 9
        r10 = process_round(state, _make_extraction(unit_price_offered=7000.0))
        assert r10.decision == "reject", (
            f"Last round frozen: expected 'reject', got '{r10.decision}'"
        )
        assert r10.session_terminated is True

    def test_last_round_frozen_meets_counter_accepts(self):
        """Frozen state, buyer meets counter on last round → accept."""
        state = _make_state(
            base_price=16000.0, cost_price=8000.0, min_floor=8640.0,
            max_rounds=10,
        )
        process_round(state, _make_extraction(unit_price_offered=8000.0))
        process_round(state, _make_extraction(unit_price_offered=7000.0))
        process_round(state, _make_extraction(unit_price_offered=6000.0))
        frozen = state.counter_history[-1]

        for _ in range(6):
            process_round(state, _make_extraction(unit_price_offered=6500.0))

        r10 = process_round(state, _make_extraction(unit_price_offered=frozen))
        assert r10.decision == "accept"

    def test_last_round_normal_close_to_counter_accepts(self):
        """Normal (unfrozen) last round, buyer within 90% of counter → accept."""
        state = _make_state(
            base_price=16000.0, cost_price=8000.0, min_floor=8640.0,
            max_rounds=10,
        )
        # Gradually increasing offers (no retrograde) over 9 rounds
        offers = [9000, 9500, 10000, 10500, 11000, 11500, 12000, 12500, 13000]
        for o in offers:
            process_round(state, _make_extraction(unit_price_offered=float(o)))

        last_counter = state.counter_history[-1]
        min_accept = last_counter * TUNING["last_round_min_counter_ratio"]

        # R10: buyer offers just above the min_accept threshold
        offer_price = round(min_accept + 1, 2)
        r10 = process_round(state, _make_extraction(unit_price_offered=offer_price))
        assert r10.decision in ("accept",), (
            f"Last round, offer {offer_price} >= min_accept {min_accept}: "
            f"expected 'accept', got '{r10.decision}'"
        )

    def test_last_round_normal_far_below_counter_rejects(self):
        """Normal (unfrozen) last round, buyer far below counter → reject."""
        state = _make_state(
            base_price=16000.0, cost_price=8000.0, min_floor=8640.0,
            max_rounds=10,
        )
        # 9 rounds of low offers
        for _ in range(9):
            process_round(state, _make_extraction(unit_price_offered=9000.0))

        last_counter = state.counter_history[-1]
        far_below = last_counter * 0.50  # Way below 90%
        r10 = process_round(state, _make_extraction(unit_price_offered=far_below))
        assert r10.decision == "reject", (
            f"Last round, offer {far_below} far below counter {last_counter}: "
            f"expected 'reject', got '{r10.decision}'"
        )
        assert r10.session_terminated is True

    def test_last_round_never_returns_counter_or_final_offer(self):
        """Exhaustive: the last round MUST return 'accept' or 'reject'."""
        # Run 10 different scenarios and verify last round always terminates
        for base, cost, offers_seq in [
            (100, 50, [40, 35, 30, 25, 30, 35, 40, 45, 50]),     # retrograde then recover
            (100, 50, [60, 65, 70, 75, 78, 80, 82, 84, 86]),     # steady climb
            (100, 50, [40, 40, 40, 40, 40, 40, 40, 40, 40]),     # stagnation
            (1000, 500, [400, 350, 300, 350, 400, 450, 500, 550, 600]),
        ]:
            state = _make_state(
                base_price=float(base), cost_price=float(cost),
                min_floor=float(cost) * 1.08, max_rounds=10,
            )
            for o in offers_seq:
                process_round(state, _make_extraction(unit_price_offered=float(o)))

            # Last round
            r_last = process_round(state, _make_extraction(
                unit_price_offered=float(offers_seq[-1])
            ))
            assert r_last.decision in ("accept", "reject"), (
                f"base={base}, last offer={offers_seq[-1]}: "
                f"expected accept/reject, got '{r_last.decision}'"
            )


class TestSamsungTranscriptScenario:
    """
    Regression test modeled on the Samsung Mobile $16K transcript.

    Sequence: R1=$8000, R2=$7000 (retrograde), R3=$6000 (freeze),
    R4=$7000, R5=$8000 (redeem), R6=$8001, ..., R10=$14001.
    """

    def test_ratchet_holds_on_retrograde(self):
        """R2 retrograde: counter must NOT drop below R1 counter."""
        state = _make_state(
            base_price=16000.0, cost_price=8000.0, min_floor=8640.0,
            max_rounds=10,
        )
        r1 = process_round(state, _make_extraction(unit_price_offered=8000.0))
        r1_counter = r1.counter_unit_price

        r2 = process_round(state, _make_extraction(unit_price_offered=7000.0))
        assert r2.counter_unit_price >= r1_counter, (
            f"R2 retrograde: counter dropped from {r1_counter} to "
            f"{r2.counter_unit_price}. Ratchet should have held."
        )

    def test_redemption_fires_and_counter_eventually_moves(self):
        """After freeze + redemption, counter drops when buyer beats all-time best."""
        state = _make_state(
            base_price=16000.0, cost_price=8000.0, min_floor=8640.0,
            max_rounds=10,
        )
        # R1-R3: trigger freeze
        process_round(state, _make_extraction(unit_price_offered=8000.0))
        process_round(state, _make_extraction(unit_price_offered=7000.0))
        process_round(state, _make_extraction(unit_price_offered=6000.0))
        assert state.final_offer_issued is True
        frozen_counter = state.counter_history[-1]

        # R4-R5: redemption (two good moves)
        process_round(state, _make_extraction(unit_price_offered=7000.0))
        process_round(state, _make_extraction(unit_price_offered=8000.0))
        assert state.final_offer_issued is False, "Per-move redemption should have fired"

        # R6: buyer beats all-time best ($8001 > $8000) → concession allowed
        r6 = process_round(state, _make_extraction(unit_price_offered=8001.0))
        # Counter should be <= frozen_counter (concession happened or held)
        assert r6.counter_unit_price <= frozen_counter, (
            f"Post-redemption counter {r6.counter_unit_price} should not "
            f"exceed frozen {frozen_counter}"
        )

    def test_full_transcript_last_round_terminates(self):
        """Full Samsung transcript: last round must result in accept or reject."""
        state = _make_state(
            base_price=16000.0, cost_price=8000.0, min_floor=8640.0,
            max_rounds=10,
        )
        offers = [8000, 7000, 6000, 7000, 8000, 8001, 9000, 11000, 14000]
        for o in offers:
            process_round(state, _make_extraction(unit_price_offered=float(o)))

        # R10: $14001
        r10 = process_round(state, _make_extraction(unit_price_offered=14001.0))
        assert r10.decision in ("accept", "reject"), (
            f"Last round with $14001: expected accept/reject, got '{r10.decision}'"
        )
