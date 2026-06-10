"""
Profit-Rational Adaptive Negotiation Engine — Extended (PRANE-X)

Pure, deterministic negotiation logic. No I/O. No LLM. No randomness.

The ONLY public entry point is process_round().
All tuning constants live in the TUNING dict at module top.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional  
import structlog

logger = structlog.get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# TUNING — every magic number in the engine lives here
# ═══════════════════════════════════════════════════════════════════════════════

TUNING = {

    # ── Floor margins ────────────────────────────────────────
    "margin_buffer_max_profit":             0.08,
    "margin_buffer_min_loss":               0.03,

    # ── Inventory pressure ───────────────────────────────────
    "inv_scarce_threshold":                 0.20,
    "inv_scarce_multiplier":                1.12,
    "inv_low_threshold":                    0.50,
    "inv_low_multiplier":                   1.06,
    "inv_surplus_threshold":                2.00,
    "inv_surplus_multiplier":               0.96,

    # ── Bulk discount (floor) ──────────────────────────────────
    "bulk_discount_rate":                   0.10,
    "bulk_discount_cap":                    0.15,
    "bulk_discount_min_qty":                2,

    # ── Bulk target (starting counter for multi-unit orders) ──
    "bulk_target_log_base":                 50,
    "bulk_target_rate":                     0.12,
    "bulk_target_cap":                      0.15,
    "bulk_target_profit_mult":              0.65,

    # ── Scarcity lock ────────────────────────────────────────
    "scarcity_stock_threshold":             5,
    "scarcity_floor_lift":                  0.05,

    # ── Concession curve ─────────────────────────────────────
    "curve_power_max_profit":               2.2,    # was 2.8 — slightly less steep
    "curve_power_min_loss":                 1.1,    # was 1.3

    # ── BBI ──────────────────────────────────────────────────
    "bbi_start":                            50.0,
    "bbi_lowball_ratio":                    0.72,
    "bbi_lowball_penalty":                  18.0,
    "bbi_repeat_penalty":                   10.0,
    "bbi_retrograde_penalty":               22.0,
    "bbi_retrograde_after_improvement_penalty": 5.0,
    "bbi_good_move_threshold":              0.03,   # was 0.04 — recognize 3%+ as good
    "bbi_good_move_reward":                 11.0,   # was 9.0
    "bbi_small_move_threshold":             0.01,
    "bbi_small_move_reward":                3.0,
    "bbi_anchor_penalty":                   14.0,
    "bbi_anchor_ratio":                     0.50,
    "tone_deltas": {
        "cooperative":  6.0,
        "neutral":      0.0,
        "aggressive":  -9.0,
        "desperate":    3.0,
    },

    # ── Bayesian WTP ─────────────────────────────────────────
    "wtp_prior":                            0.50,
    "wtp_sigmoid_steepness":                10.0,
    "wtp_high_offer_threshold":             0.85,
    "wtp_low_offer_threshold":              0.65,
    "wtp_urgency_boost":                    0.15,
    "wtp_clamp_min":                        0.05,
    "wtp_clamp_max":                        0.95,

    # ── Offer velocity (WTP modifier) ────────────────────────
    "velocity_window":                      3,
    "velocity_high_threshold":              0.04,
    "velocity_high_wtp_penalty":            0.08,

    # ── ZOPA ─────────────────────────────────────────────────
    "zopa_wtp_to_price_factor":             1.15,
    "zopa_no_overlap_max_rounds":           4,

    # ── Historical target ────────────────────────────────────
    "target_margin_default":                0.20,
    "history_conversion_weight":            0.40,
    "history_margin_weight":                0.60,
    "history_min_sessions":                 5,

    # ── Acceptance model ─────────────────────────────────────
    "round_cost_rate":                      0.04,
    "p_improve_bbi_weight":                 0.55,
    "p_improve_velocity_weight":            0.45,
    "p_improve_clamp_min":                  0.05,
    "p_improve_clamp_max":                  0.80,

    # ── Phase thresholds ─────────────────────────────────────
    "phase_anchor_resist_rounds":           1,
    "phase_probe_fraction":                 0.35,
    "phase_concede_fraction":               0.75,

    # ── Phase concession multipliers ─────────────────────────
    "phase_multiplier": {
        "ANCHOR_RESIST":  1.00,
        "PROBING":        0.50,
        "CONCEDING":      1.00,
        "CLOSING":        1.40,
        "FINAL_OFFER":    0.00,
        "TERMINATED":     0.00,
    },

    # ── Per-round concession cap ──────────────────────────────
    "max_concession_per_round_budget_pct":  0.12,   # was 0.05

    # ── Anti-manipulation ────────────────────────────────────
    "stagnation_threshold_pct":             0.02,
    "stagnation_rounds_trigger":            2,
    "retrograde_immediate_trigger":         2,

    # ── First-offer protection ───────────────────────────────
    "round1_max_concession_pct":            0.10,
    "round1_budget_fraction":               0.12,   # was 0.04

    # ── PSIM (Price Signal Integrity Model) ──────────────────
    "psim_healthy_ratio_threshold":         0.85,
    "psim_conversion_trigger":              0.60,
    "psim_floor_lift":                      0.03,

    # ── IRGM (Inventory Risk Gradient Model) ─────────────────
    "irgm_surplus_ratio_threshold":         1.50,
    "irgm_surplus_turnover_threshold":      0.30,
    "irgm_surplus_curve_reduction":         0.25,
    "irgm_scarce_ratio_threshold":          0.30,
    "irgm_scarce_turnover_threshold":       0.70,
    "irgm_scarce_curve_increase":           0.25,
    "irgm_curve_power_min":                 0.50,

    # ── BAM (Buyer Archetype Memory) ─────────────────────────
    "bam_bbi_bias": {
        "LOWBALLER":   -10.0,
        "GRINDER":      -5.0,
        "IMPULSE":     +10.0,
        "NEGOTIATOR":    0.0,
        "UNKNOWN":       0.0,
    },
    "bam_lowball_first_offer_ratio":        0.70,
    "bam_grinder_avg_rounds":               4.0,
    "bam_grinder_acceptance_rate":          0.30,
    "bam_impulse_avg_rounds":               2.0,
    "bam_impulse_acceptance_rate":          0.60,
    "bam_min_history_sessions":             3,

    # ── Extended Utility Model ───────────────────────────────
    "utility_inventory_relief_weight":      0.10,
    "utility_price_signal_damage_weight":   0.05,
    # ── Acceptance guards ─────────────────────────────────────
    "min_acceptance_round_max_profit":      3,
    "min_acceptance_round_min_loss":        2,
    "min_acceptance_ratio_max_profit":      0.88,   # Bug C fix: restored from 0.86
    "min_acceptance_ratio_min_loss":        0.78,

    # ── Last-round acceptance guard ───────────────────────────
    #   On the final round, only accept if the buyer's offer is
    #   at least this fraction of the last counter.  Prevents
    #   accepting a lowball just because rounds ran out.
    "last_round_min_counter_ratio":         0.90,

    # ── Fair-offer proximity (Upgrade 1 — replaces redemption bridge) ─
    #   If buyer's offer >= this fraction of last counter → firmness instantly = 0.
    #   0.92 means the offer must be within 8% of the counter.
    "fair_offer_proximity_ratio":           0.92,

    # Legacy keys removed:
    # "redemption_bridge_pct", "redemption_good_moves", "redemption_cumulative_pct"
    # "post_redemption_min_rounds"

    # ── Counter ratchet (anti-yo-yo) ──────────────────────────
    "ratchet_tighten_factor":               0.15,
    "ratchet_tighten_cap":                  0.03,

    # ── Concession reciprocity (Upgrade 2) ────────────────────
    #   Scales concession based on buyer's latest price movement.
    #   reference_move is the neutral point (3% move = 1.0x multiplier).
    "reciprocity_reference_move":           0.03,
    "reciprocity_min":                      0.25,   # retrograde → 25% of normal concession
    "reciprocity_max":                      1.40,   # large buyer moves → 40% bonus

    # ── Fair engagement bonus (Upgrade 6) ─────────────────────
    #   When buyer's offer is close to last counter, apply a bonus
    #   multiplier to the concession step.
    "fair_engagement_threshold":            0.88,   # buyer within 12% of counter
    "fair_engagement_bonus":                1.25,   # 25% more generous

    # ── Graduated Firmness (replaces binary freeze) ───────────
    #   firmness_level 0=normal, 1=cautious, 2=firm, 3=final
    "firmness_large_move_pct":              0.05,   # buyer move ≥5% of base → firmness -2
    "firmness_good_move_pct":               0.02,   # buyer move ≥2% of base → firmness -1
    "firmness_concession_mults":            [1.0, 0.50, 0.15, 0.0],  # per firmness level

    # ── Proximity gate (Patch 3 — concession algorithm redesign) ──
    #   Maps buyer proximity (offer / counter) to a concession gate
    #   multiplier.  Linear interpolation between breakpoints.
    #   Far buyers get near-zero concessions; close buyers get bonuses.
    "proximity_gate_breakpoints": [
        (0.00, 0.03),   # buyer < 65% of counter: 3% of normal (near-zero)
        (0.65, 0.03),   # flat floor zone
        (0.78, 0.18),   # 65–78%: 18% (small, warming up)
        (0.87, 0.55),   # 78–87%: 55% (moderate, approaching fair)
        (0.93, 1.00),   # 87–93%: 100% (normal, fair zone)
        (0.97, 1.30),   # 93–97%: 130% (generous, closing)
        (1.01, 1.50),   # 97%+:   150% (push to close)
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class NegotiationPhase(str, Enum):
    ANCHOR_RESIST = "ANCHOR_RESIST"
    PROBING       = "PROBING"
    CONCEDING     = "CONCEDING"
    CLOSING       = "CLOSING"
    FINAL_OFFER   = "FINAL_OFFER"
    TERMINATED    = "TERMINATED"


class BuyerArchetype(str, Enum):
    UNKNOWN    = "UNKNOWN"
    LOWBALLER  = "LOWBALLER"
    GRINDER    = "GRINDER"
    IMPULSE    = "IMPULSE"
    NEGOTIATOR = "NEGOTIATOR"


class ReasoningTag(str, Enum):
    FLOOR_ENFORCED        = "FLOOR_ENFORCED"
    ROUND1_HOLD           = "ROUND1_HOLD"
    BBI_LOWBALL           = "BBI_LOWBALL"
    BBI_PENALTY           = "BBI_PENALTY"
    BBI_REWARD            = "BBI_REWARD"
    ANCHOR_RESIST         = "ANCHOR_RESIST"
    BAYESIAN_HOLD         = "BAYESIAN_HOLD"
    ZOPA_NO_OVERLAP       = "ZOPA_NO_OVERLAP"
    PHASE_CONCEDE         = "PHASE_CONCEDE"
    PHASE_CLOSE           = "PHASE_CLOSE"
    STAGNATION_FINAL      = "STAGNATION_FINAL"
    RETROGRADE_FINAL      = "RETROGRADE_FINAL"
    BUDGET_EXHAUSTED      = "BUDGET_EXHAUSTED"
    UTILITY_ACCEPT        = "UTILITY_ACCEPT"
    LAST_ROUND_ACCEPT     = "LAST_ROUND_ACCEPT"
    LAST_ROUND_REJECT     = "LAST_ROUND_REJECT"
    BELOW_FLOOR_REJECT    = "BELOW_FLOOR_REJECT"
    SCARCITY_LOCK         = "SCARCITY_LOCK"
    BUNDLE_DEFLECT        = "BUNDLE_DEFLECT"
    SOCIAL_PROOF_RESIST   = "SOCIAL_PROOF_RESIST"
    HISTORICAL_TARGET     = "HISTORICAL_TARGET"
    PSIM_FLOOR_RAISED     = "PSIM_FLOOR_RAISED"
    IRGM_CURVE_ADJUSTED   = "IRGM_CURVE_ADJUSTED"
    BAM_BIAS_APPLIED      = "BAM_BIAS_APPLIED"
    EXTENDED_UTILITY      = "EXTENDED_UTILITY"


# ═══════════════════════════════════════════════════════════════════════════════
# MATH HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-clamp(x, -500.0, 500.0)))


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _bbi_category(bbi: float) -> str:
    if bbi < 33.0:
        return "hostile"
    if bbi < 67.0:
        return "neutral"
    return "cooperative"


# ═══════════════════════════════════════════════════════════════════════════════
# BULK TARGET PRICE  (public — also used by pricing_agent for initial offer)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_bulk_target_price(
    base_price: float,
    quantity: int,
    mode: str,
) -> float:
    """
    Compute the quantity-discounted starting price for a multi-unit order.

    For qty=1, returns base_price (no discount).
    For qty>1, applies a smooth log-scaled discount that grows with
    quantity but has diminishing returns.

    This is a PUBLIC helper — called by the engine's NegotiationState
    and by PricingStrategyAgent.compute_initial_offer().
    """
    T = TUNING
    if quantity <= 1:
        return base_price

    raw_pct = math.log(quantity) / math.log(T["bulk_target_log_base"]) * T["bulk_target_rate"]
    if mode == "MAX_PROFIT":
        raw_pct *= T["bulk_target_profit_mult"]
    raw_pct = min(raw_pct, T["bulk_target_cap"])

    target = base_price * (1 - raw_pct)
    return round(max(target, 0.01), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE RESULT  (frozen — immutable once created)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EngineResult:
    decision:                     str           # "accept"|"counter"|"reject"|"final_offer"
    counter_unit_price:           float
    counter_total_price:          float
    dynamic_floor:                float
    reasoning_tag:                ReasoningTag
    phase:                        NegotiationPhase
    buyer_archetype:              BuyerArchetype
    bbi:                          float
    bbi_category:                 str           # "hostile"|"neutral"|"cooperative"
    p_high_wtp:                   float
    round_number:                 int
    rounds_remaining:             int
    remaining_concession_budget:  float
    zopa_estimated_buyer_ceiling: float
    psim_triggered:               bool
    irgm_triggered:               bool
    session_terminated:           bool


# ═══════════════════════════════════════════════════════════════════════════════
# NEGOTIATION STATE  (mutable — persisted in TTLCache across rounds)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NegotiationState:

    # ── Product economics (required at construction) ──────────
    base_price:                 float
    cost_price:                 float
    min_floor:                  float
    mode:                       str       # "MAX_PROFIT" | "MIN_LOSS"
    max_rounds:                 int
    quantity:                   int

    # ── Historical product performance ───────────────────────
    total_sessions:             int
    accepted_deals:             int
    historical_avg_margin:      float
    historical_revenue:         float

    # ── Inventory ─────────────────────────────────────────────
    available_inventory:        int
    reference_inventory:        int

    # ── Buyer archetype (derived before construction) ─────────
    buyer_archetype:            BuyerArchetype = BuyerArchetype.UNKNOWN

    # ── Computed in __post_init__ ─────────────────────────────
    inventory_ratio:            float           = field(init=False)
    dynamic_floor:              float           = field(init=False)
    bulk_target_price:          float           = field(init=False)
    historical_target:          float           = field(init=False)
    total_concession_budget:    float           = field(init=False)
    remaining_concession_budget: float          = field(init=False)
    phase:                      NegotiationPhase = field(init=False)
    bbi:                        float           = field(init=False)
    p_high_wtp:                 float           = field(init=False)

    # ── Round tracking ────────────────────────────────────────
    current_round:              int             = field(default=0)
    offer_history:              list[float]     = field(default_factory=list)
    counter_history:            list[float]     = field(default_factory=list)

    # ── Anti-manipulation / firmness counters ────────────────
    consecutive_stagnant:       int             = field(default=0)
    retrograde_count:           int             = field(default=0)   # logging only
    anchoring_penalty_done:     bool            = field(default=False)
    manipulation_events:        int             = field(default=0)
    zopa_no_overlap_count:      int             = field(default=0)
    scarcity_locked:            bool            = field(default=False)

    # ── Graduated firmness (replaces binary final_offer_issued) ──
    #   0=normal, 1=cautious, 2=firm, 3=final (no concession)
    firmness_level:             int             = field(default=0)

    # ── Last engine result (set by _build_result for verbalize access) ─
    _last_result:               Optional["EngineResult"] = field(default=None)

    # ── Last buyer message (for verbalize context — Patch 3) ──
    _last_buyer_message:        Optional[str] = field(default=None)

    def __post_init__(self) -> None:
        T = TUNING

        # 1. BBI with archetype bias applied immediately
        self.bbi = clamp(
            T["bbi_start"] + T["bam_bbi_bias"][self.buyer_archetype.value],
            0.0, 100.0
        )

        # 2. WTP prior
        self.p_high_wtp = T["wtp_prior"]

        # 3. Inventory ratio
        self.inventory_ratio = self.available_inventory / max(self.reference_inventory, 1)

        # 4. Dynamic floor (includes all inventory and bulk layers)
        self.dynamic_floor = _compute_dynamic_floor(self)

        # 5. PSIM check — may raise dynamic_floor
        self.dynamic_floor = _apply_psim(self)

        # 6. Scarcity lock — may raise dynamic_floor further
        self.scarcity_locked = (
            (self.available_inventory - self.quantity) < T["scarcity_stock_threshold"]
        )
        if self.scarcity_locked:
            self.dynamic_floor = round(
                min(self.dynamic_floor * (1 + T["scarcity_floor_lift"]), self.base_price),
                2,
            )

        # 7. Historical target price
        self.historical_target = _compute_historical_target(self)

        # 8. Bulk target (quantity-discounted starting price for counters)
        self.bulk_target_price = max(
            compute_bulk_target_price(self.base_price, self.quantity, self.mode),
            self.dynamic_floor,
        )

        # 9. Concession budget (from base_price to floor — full range)
        budget = (self.base_price - self.dynamic_floor) * self.quantity
        self.total_concession_budget = max(budget, 0.0)
        self.remaining_concession_budget = self.total_concession_budget

        # 10. Initial phase
        self.phase = NegotiationPhase.ANCHOR_RESIST


# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMIC FLOOR
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_dynamic_floor(s: NegotiationState) -> float:
    T = TUNING

    # Layer 1: Mode-based margin floor
    buf = T["margin_buffer_max_profit"] if s.mode == "MAX_PROFIT" else T["margin_buffer_min_loss"]
    mode_floor = max(s.min_floor, s.cost_price * (1 + buf))

    # Layer 2: Inventory multiplier
    r = s.inventory_ratio
    if r < T["inv_scarce_threshold"]:
        inv_m = T["inv_scarce_multiplier"]
    elif r < T["inv_low_threshold"]:
        inv_m = T["inv_low_multiplier"]
    elif r > T["inv_surplus_threshold"]:
        inv_m = T["inv_surplus_multiplier"]
    else:
        inv_m = 1.00

    # Layer 3: Bulk discount (log-scaled)
    if s.quantity >= T["bulk_discount_min_qty"]:
        raw = math.log(s.quantity + 1) / math.log(51)
        bulk_disc = min(raw * T["bulk_discount_rate"], T["bulk_discount_cap"])
        if s.mode == "MAX_PROFIT":
            bulk_disc *= 0.65
    else:
        bulk_disc = 0.0

    floor = mode_floor * inv_m * (1 - bulk_disc)

    # Hard constraint: floor can never drop below true cost
    return round(max(floor, s.cost_price), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# PSIM — Price Signal Integrity Model
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_psim(s: NegotiationState) -> float:
    """
    Returns the (possibly raised) dynamic_floor.
    Called in __post_init__ after _compute_dynamic_floor.
    """
    T = TUNING

    if s.total_sessions < T["history_min_sessions"]:
        return s.dynamic_floor

    conversion_rate = s.accepted_deals / s.total_sessions

    avg_margin_safe = clamp(s.historical_avg_margin, 0.01, 0.99)
    implied_close_price = s.cost_price / (1 - avg_margin_safe)

    healthy_close_ratio = implied_close_price / s.base_price

    if (healthy_close_ratio < T["psim_healthy_ratio_threshold"]
            and conversion_rate > T["psim_conversion_trigger"]):
        lifted = s.dynamic_floor + T["psim_floor_lift"] * s.base_price
        return round(min(lifted, s.base_price), 2)

    return s.dynamic_floor


# ═══════════════════════════════════════════════════════════════════════════════
# HISTORICAL TARGET PRICE
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_historical_target(s: NegotiationState) -> float:
    T = TUNING

    if s.total_sessions < T["history_min_sessions"]:
        target_margin = T["target_margin_default"]
        return round(max(s.cost_price * (1 + target_margin), s.dynamic_floor), 2)

    conversion_rate = s.accepted_deals / s.total_sessions

    if conversion_rate < 0.15:
        conversion_adjustment = -0.04
    elif conversion_rate > T["psim_conversion_trigger"]:
        conversion_adjustment = +0.03
    else:
        conversion_adjustment = 0.0

    target_margin = T["target_margin_default"]
    if s.historical_avg_margin < target_margin - 0.05:
        margin_adjustment = +0.03
    elif s.historical_avg_margin > target_margin + 0.05:
        margin_adjustment = -0.02
    else:
        margin_adjustment = 0.0

    composite = (
        T["history_conversion_weight"] * conversion_adjustment
        + T["history_margin_weight"] * margin_adjustment
    )

    raw_target = s.base_price * (1 + composite)
    return round(clamp(raw_target, s.dynamic_floor, s.base_price), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# BUYER ARCHETYPE DERIVATION  (called externally in pricing_agent.py)
# ═══════════════════════════════════════════════════════════════════════════════

def derive_archetype(session_history: list[dict]) -> BuyerArchetype:
    """
    Derive buyer archetype from historical session records.

    Each record is a dict with keys:
        offered_price, counter_price, total_rounds, decision
    """
    T = TUNING

    if len(session_history) < T["bam_min_history_sessions"]:
        return BuyerArchetype.UNKNOWN

    first_offer_ratios = [
        r["offered_price"] / max(r["counter_price"], 0.01)
        for r in session_history
        if r.get("offered_price") and r.get("counter_price")
    ]
    avg_first_offer_ratio = (
        sum(first_offer_ratios) / len(first_offer_ratios)
        if first_offer_ratios
        else 1.0
    )

    avg_rounds = sum(r["total_rounds"] for r in session_history) / len(session_history)

    acceptance_rate = sum(
        1 for r in session_history if r.get("decision") == "accept"
    ) / len(session_history)

    if avg_first_offer_ratio < T["bam_lowball_first_offer_ratio"]:
        return BuyerArchetype.LOWBALLER

    if avg_rounds > T["bam_grinder_avg_rounds"] and acceptance_rate < T["bam_grinder_acceptance_rate"]:
        return BuyerArchetype.GRINDER

    if avg_rounds <= T["bam_impulse_avg_rounds"] and acceptance_rate > T["bam_impulse_acceptance_rate"]:
        return BuyerArchetype.IMPULSE

    return BuyerArchetype.NEGOTIATOR


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE DETERMINATION
# ═══════════════════════════════════════════════════════════════════════════════

def _determine_phase(s: NegotiationState) -> NegotiationPhase:
    T = TUNING
    if s.firmness_level >= 3:
        return NegotiationPhase.FINAL_OFFER
    progress = s.current_round / s.max_rounds
    anchor_boundary = T["phase_anchor_resist_rounds"] / s.max_rounds
    if progress <= anchor_boundary:
        raw_phase = NegotiationPhase.ANCHOR_RESIST
    elif progress <= T["phase_probe_fraction"]:
        raw_phase = NegotiationPhase.PROBING
    elif progress <= T["phase_concede_fraction"]:
        raw_phase = NegotiationPhase.CONCEDING
    else:
        raw_phase = NegotiationPhase.CLOSING

    return raw_phase


# ═══════════════════════════════════════════════════════════════════════════════
# ZOPA ESTIMATOR
# ═══════════════════════════════════════════════════════════════════════════════

def _estimate_buyer_ceiling(s: NegotiationState) -> float:
    T = TUNING
    raw = (
        s.dynamic_floor
        + (s.base_price - s.dynamic_floor)
        * s.p_high_wtp
        * T["zopa_wtp_to_price_factor"]
    )
    return round(clamp(raw, s.dynamic_floor, s.base_price), 2)


def _extrapolate_buyer_ceiling(s: NegotiationState) -> float:
    """
    If we have 3+ buyer offers, fit a linear trend and project where
    the buyer will top out (their estimated ceiling).  Falls back to
    the WTP-based estimate with fewer offers.
    """
    if len(s.offer_history) < 3:
        return _estimate_buyer_ceiling(s)

    # Use last 4 offers max for recency bias
    recent = s.offer_history[-4:]
    n = len(recent)

    # Simple linear regression: offer index → price
    xs = list(range(n))
    x_mean = (n - 1) / 2
    y_mean = sum(recent) / n

    num = sum((xs[i] - x_mean) * (recent[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))

    if den == 0:
        return _estimate_buyer_ceiling(s)

    slope = num / den

    # Project 2 more rounds ahead
    projected = recent[-1] + slope * 2

    # Blend with WTP estimate (50/50 when we have evidence)
    wtp_estimate = _estimate_buyer_ceiling(s)
    blended = (projected + wtp_estimate) / 2

    return round(clamp(blended, s.dynamic_floor, s.base_price), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# BBI UPDATE
# ═══════════════════════════════════════════════════════════════════════════════

def _update_bbi(
    s: NegotiationState,
    extraction: dict,
) -> tuple[float, Optional[ReasoningTag]]:
    T = TUNING
    bbi = s.bbi
    tag: Optional[ReasoningTag] = None
    buyer_unit = extraction["resolved_unit_price"]

    # A) Lowball
    if buyer_unit < s.dynamic_floor * T["bbi_lowball_ratio"]:
        bbi -= T["bbi_lowball_penalty"]
        tag = ReasoningTag.BBI_LOWBALL

    # B) Offer trajectory
    if len(s.offer_history) >= 2:
        prev = s.offer_history[-2]
        curr = s.offer_history[-1]
        improvement = (curr - prev) / prev if prev != 0 else 0.0
        prev_improvement = (
            (s.offer_history[-2] - s.offer_history[-3]) / s.offer_history[-3]
            if len(s.offer_history) >= 3 and s.offer_history[-3] != 0
            else 0.0
        )

        if improvement < 0:
            s.retrograde_count += 1
            bbi -= T["bbi_retrograde_penalty"]
            if prev_improvement >= T["bbi_good_move_threshold"]:
                bbi -= T["bbi_retrograde_after_improvement_penalty"]
        elif improvement == 0:
            bbi -= T["bbi_repeat_penalty"]
            s.consecutive_stagnant += 1
        elif improvement >= T["bbi_good_move_threshold"]:
            bbi += T["bbi_good_move_reward"]
            s.consecutive_stagnant = 0
        elif improvement >= T["bbi_small_move_threshold"]:
            bbi += T["bbi_small_move_reward"]
            s.consecutive_stagnant = 0
        else:
            # 0 < improvement < small_move_threshold — buyer IS
            # moving, just slowly.  Reset stagnation counter;
            # only exact repeats (improvement == 0) count as stagnant.
            s.consecutive_stagnant = 0

    # C) Tone modifier
    bbi += T["tone_deltas"].get(extraction.get("tone", "neutral"), 0.0)

    # D) Anchoring penalty (applied once per session)
    if extraction.get("anchoring_detected") and not s.anchoring_penalty_done:
        if buyer_unit < s.base_price * T["bbi_anchor_ratio"]:
            bbi -= T["bbi_anchor_penalty"]
            s.anchoring_penalty_done = True
            tag = ReasoningTag.ANCHOR_RESIST

    # E) Urgency signal → boost WTP belief
    if extraction.get("urgency_signal"):
        s.p_high_wtp = clamp(
            s.p_high_wtp + T["wtp_urgency_boost"],
            T["wtp_clamp_min"], T["wtp_clamp_max"],
        )

    # F) Competitor price claim → legitimate tactic, don't penalize
    if extraction.get("competitor_price_claim"):
        s.p_high_wtp = clamp(
            s.p_high_wtp + 0.05,
            T["wtp_clamp_min"], T["wtp_clamp_max"],
        )

    return clamp(bbi, 0.0, 100.0), tag


# ═══════════════════════════════════════════════════════════════════════════════
# BAYESIAN WTP UPDATE
# ═══════════════════════════════════════════════════════════════════════════════

def _update_wtp(s: NegotiationState) -> float:
    T = TUNING
    buyer_unit = s.offer_history[-1]
    offer_ratio = buyer_unit / s.base_price

    p_high = sigmoid(T["wtp_sigmoid_steepness"] * (offer_ratio - T["wtp_high_offer_threshold"]))
    p_low = sigmoid(T["wtp_sigmoid_steepness"] * (T["wtp_low_offer_threshold"] - offer_ratio))

    prior = s.p_high_wtp
    denom = p_high * prior + p_low * (1 - prior)
    posterior = (p_high * prior) / denom if denom > 0 else prior

    # Offer velocity modifier
    if len(s.offer_history) >= T["velocity_window"]:
        window = s.offer_history[-T["velocity_window"]:]
        avg_velocity = sum(
            (window[i] - window[i - 1]) / max(window[i - 1], 0.01)
            for i in range(1, len(window))
        ) / (len(window) - 1)
        if avg_velocity > T["velocity_high_threshold"]:
            posterior -= T["velocity_high_wtp_penalty"]

    return clamp(posterior, T["wtp_clamp_min"], T["wtp_clamp_max"])


# ═══════════════════════════════════════════════════════════════════════════════
# PROXIMITY GATE  (Patch 3 — dominant concession control)
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_proximity_gate(proximity: float) -> float:
    """
    Maps buyer proximity (offer / current_counter) to a concession gate multiplier.
    proximity < 0.65 → near-zero (buyer must close the gap)
    proximity > 0.93 → generous (buyer is close, push to close)
    Uses linear interpolation between breakpoints.
    """
    pts = TUNING["proximity_gate_breakpoints"]
    for i in range(len(pts) - 1):
        lo_p, lo_g = pts[i]
        hi_p, hi_g = pts[i + 1]
        if lo_p <= proximity <= hi_p:
            t = (proximity - lo_p) / (hi_p - lo_p) if hi_p != lo_p else 0.0
            return lo_g + t * (hi_g - lo_g)
    return pts[-1][1]  # above all breakpoints


# ═══════════════════════════════════════════════════════════════════════════════
# CONCESSION COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_concession(s: NegotiationState, u_price: float) -> tuple[float, ReasoningTag]:
    T = TUNING

    if s.remaining_concession_budget <= 0:
        return s.dynamic_floor, ReasoningTag.BUDGET_EXHAUSTED

    # ── Base curve power ──────────────────────────────────────
    curve_power = (
        T["curve_power_max_profit"] if s.mode == "MAX_PROFIT"
        else T["curve_power_min_loss"]
    )

    # ── IRGM: Inventory Risk Gradient adjustment ──────────────
    turnover_proxy = (
        s.historical_revenue / max(s.total_sessions, 1)
    ) / max(s.base_price, 0.01)

    irgm_tag: Optional[ReasoningTag] = None
    if (s.inventory_ratio > T["irgm_surplus_ratio_threshold"]
            and turnover_proxy < T["irgm_surplus_turnover_threshold"]):
        curve_power -= T["irgm_surplus_curve_reduction"]
        irgm_tag = ReasoningTag.IRGM_CURVE_ADJUSTED

    elif (s.inventory_ratio < T["irgm_scarce_ratio_threshold"]
            and turnover_proxy > T["irgm_scarce_turnover_threshold"]):
        curve_power += T["irgm_scarce_curve_increase"]
        irgm_tag = ReasoningTag.IRGM_CURVE_ADJUSTED

    curve_power = max(curve_power, T["irgm_curve_power_min"])

    # ── Round pressure ────────────────────────────────────────
    round_pressure = s.current_round / s.max_rounds

    # ── Phase multiplier ──────────────────────────────────────
    phase_mult = T["phase_multiplier"][s.phase.value]

    # ── BBI concession multiplier ─────────────────────────────
    bbi_mult = clamp(0.4 + (s.bbi / 166.7), 0.4, 1.0)

    # ── Bayesian hold factor ──────────────────────────────────
    wtp_hold = 0.5 + (s.p_high_wtp * 0.5)

    # ── Scarcity reduction ────────────────────────────────────
    scarcity_factor = 0.55 if s.scarcity_locked else 1.0

    # ── Historical target pull ────────────────────────────────
    last_counter = s.counter_history[-1] if s.counter_history else s.bulk_target_price
    if last_counter <= s.historical_target:
        historical_factor = 0.40
        tag = ReasoningTag.HISTORICAL_TARGET
    else:
        historical_factor = 1.00
        tag = irgm_tag or (
            ReasoningTag.PHASE_CLOSE if s.phase == NegotiationPhase.CLOSING
            else ReasoningTag.PHASE_CONCEDE
        )

    # ── First-round concession ─────────────────────────────
    #   Round 1 uses a fixed fraction of the total budget instead
    #   of the exponential curve (which produces near-zero at t=0.1).
    #   The cap prevents oversized R1 concessions on expensive items.
    if s.current_round == 1:
        budget_frac = s.remaining_concession_budget * T["round1_budget_fraction"]
        max_r1 = s.base_price * T["round1_max_concession_pct"] * s.quantity
        base_step = min(budget_frac, max_r1)
        tag = ReasoningTag.ROUND1_HOLD
    else:
        base_step = s.remaining_concession_budget * (round_pressure ** curve_power)

    # ── PROXIMITY GATE — applied to base_step, dominant control ──
    #   Computed AFTER base_step but BEFORE all other multipliers.
    #   Far-away buyers get tiny concessions regardless of BBI,
    #   budget size, or round pressure.
    proximity = u_price / last_counter if last_counter > 0 else 0.5
    proximity_gate = _compute_proximity_gate(proximity)
    base_step_gated = base_step * proximity_gate

    # ── Reciprocity signal (Upgrade 2) ────────────────────────
    #   Scale concession based on buyer's latest price movement
    #   relative to their previous best offer.
    reciprocity_mult = 1.0
    if len(s.offer_history) >= 2:
        buyer_prev_best = max(s.offer_history[:-1])
        buyer_move_pct = (s.offer_history[-1] - buyer_prev_best) / s.base_price
        if buyer_move_pct > 0:
            raw_r = buyer_move_pct / T["reciprocity_reference_move"]
            reciprocity_mult = clamp(raw_r, T["reciprocity_min"], T["reciprocity_max"])
        else:
            reciprocity_mult = T["reciprocity_min"]

    # ── Graduated firmness multiplier ─────────────────────────
    firmness_mult = T["firmness_concession_mults"][min(s.firmness_level, 3)]

    # ── Composite concession step (total across all units) ────
    #   Uses gated base_step — proximity gate is the dominant control.
    concession_step = (
        base_step_gated
        * bbi_mult
        * (1.0 / wtp_hold)
        * scarcity_factor
        * historical_factor
        * phase_mult
        * reciprocity_mult
        * firmness_mult
    )

    # ── Per-round concession cap ──────────────────────────────
    #   Prevents single-round concession dumps.
    max_round = s.remaining_concession_budget * T["max_concession_per_round_budget_pct"]
    concession_step = min(concession_step, max_round)

    concession_per_unit = concession_step / s.quantity
    raw_counter = last_counter - concession_per_unit
    counter_price = round(max(raw_counter, s.dynamic_floor), 2)

    # Deduct actual concession from budget
    actual = (last_counter - counter_price) * s.quantity
    s.remaining_concession_budget = max(s.remaining_concession_budget - actual, 0.0)

    return counter_price, tag


# ═══════════════════════════════════════════════════════════════════════════════
# EXTENDED UTILITY ACCEPTANCE
# ═══════════════════════════════════════════════════════════════════════════════

def _should_accept(
    s: NegotiationState,
    buyer_unit: float,
    next_counter: float,
) -> bool:
    """
    Marginal gain-vs-cost acceptance model.

    Decides whether to accept the current offer or continue negotiating.
    Uses a MARGINAL comparison: accept when the expected improvement
    from continuing does not justify the cost of delay.  Previous
    version compared absolute profit (which scales with price level)
    against incremental gain (which does not), causing instant
    acceptance on expensive, high-margin items.
    """
    T = TUNING

    # ── ABSOLUTE FLOOR — runs before everything, no bypass ────
    #   Patch 3 Bug A: $561/$999 = 56.1% was accepted because
    #   firmness_level=3 relaxed min_ratio to floor ratio. This
    #   hard pre-check ensures min_acceptance_ratio is NEVER bypassed.
    offer_ratio = buyer_unit / s.base_price
    min_ratio = (
        T["min_acceptance_ratio_max_profit"]
        if s.mode == "MAX_PROFIT"
        else T["min_acceptance_ratio_min_loss"]
    )
    if offer_ratio < min_ratio:
        return False  # Hard stop. No utility model, no budget state, no round can bypass this.

    # ── Hard floor ────────────────────────────────────────────
    if buyer_unit < s.dynamic_floor:
        return False

    # ── Guard 1: Minimum rounds before acceptance ─────────────
    #   Waived when firmness is at level 3 (final offer) — we
    #   already signalled urgency, accept any above-floor response.
    #   Patch 3 Bug B Fix 1: -1 allows acceptance on the final eligible round.
    min_round = (
        T["min_acceptance_round_max_profit"]
        if s.mode == "MAX_PROFIT"
        else T["min_acceptance_round_min_loss"]
    )
    if s.current_round < min_round - 1 and s.firmness_level < 3:
        return False


    # (Guard 2 removed — the ABSOLUTE FLOOR pre-check at the top
    #  of this function now handles min_ratio unconditionally.
    #  The old Guard 2 allowed firmness=3 to relax the ratio,
    #  which caused Patch 3 Bug A.)


    # ── Probability of buyer improving ────────────────────────
    rounds_left = s.max_rounds - s.current_round

    bbi_component = (s.bbi / 100.0) * T["p_improve_bbi_weight"]
    if len(s.offer_history) >= 2:
        recent_v = (
            (s.offer_history[-1] - s.offer_history[-2])
            / max(s.offer_history[-2], 0.01)
        )
        v_component = (
            clamp(recent_v / 0.10, 0.0, 1.0)
            * T["p_improve_velocity_weight"]
        )
    else:
        v_component = 0.1 * T["p_improve_velocity_weight"]

    p_improve = clamp(
        bbi_component + v_component,
        T["p_improve_clamp_min"],
        T["p_improve_clamp_max"],
    )

    # ── Expected marginal gain from continuing ────────────────
    price_gap = next_counter - buyer_unit  # per-unit gap
    expected_gain = (
        price_gap * s.quantity * p_improve
        * (rounds_left / s.max_rounds)
    )
    discount_factor = (1 - T["round_cost_rate"]) ** rounds_left
    discounted_gain = expected_gain * discount_factor

    # ── Inventory relief (incentive to accept now) ────────────
    inventory_relief = (
        (s.quantity / max(s.available_inventory, 1))
        * s.base_price
        * T["utility_inventory_relief_weight"]
    )

    # ── Price signal damage (penalty for accepting low) ───────
    price_signal_damage = (
        (1.0 - offer_ratio)
        * s.base_price
        * T["utility_price_signal_damage_weight"]
    )

    # ── Decision: accept when net benefit of waiting <= 0 ─────
    net_benefit_of_waiting = (
        discounted_gain + price_signal_damage - inventory_relief
    )
    return net_benefit_of_waiting <= 0


# ═══════════════════════════════════════════════════════════════════════════════
# ANTI-MANIPULATION
# ═══════════════════════════════════════════════════════════════════════════════

def _check_manipulation(
    s: NegotiationState,
    extraction: dict,
) -> Optional[ReasoningTag]:
    T = TUNING

    if (s.consecutive_stagnant >= T["stagnation_rounds_trigger"]
            and s.firmness_level < 3):
        s.firmness_level = 3
        s.manipulation_events += 1
        return ReasoningTag.STAGNATION_FINAL

    if (s.retrograde_count >= T["retrograde_immediate_trigger"]
            and s.firmness_level < 3):
        s.firmness_level = 3
        s.manipulation_events += 1
        return ReasoningTag.RETROGRADE_FINAL

    if extraction.get("bundle_request"):
        return ReasoningTag.BUNDLE_DEFLECT

    if extraction.get("social_proof_claim"):
        return ReasoningTag.SOCIAL_PROOF_RESIST

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT BUILDERS (thin wrappers around _build_result)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_result(
    s: NegotiationState,
    decision: str,
    counter_unit: float,
    tag: ReasoningTag,
    buyer_ceiling: Optional[float] = None,
    psim_triggered: bool = False,
    irgm_triggered: bool = False,
) -> EngineResult:
    result = EngineResult(
        decision=decision,
        counter_unit_price=round(counter_unit, 2),
        counter_total_price=round(counter_unit * s.quantity, 2),
        dynamic_floor=s.dynamic_floor,
        reasoning_tag=tag,
        phase=s.phase,
        buyer_archetype=s.buyer_archetype,
        bbi=round(s.bbi, 1),
        bbi_category=_bbi_category(s.bbi),
        p_high_wtp=round(s.p_high_wtp, 3),
        round_number=s.current_round,
        rounds_remaining=s.max_rounds - s.current_round,
        remaining_concession_budget=round(s.remaining_concession_budget, 2),
        zopa_estimated_buyer_ceiling=buyer_ceiling or _extrapolate_buyer_ceiling(s),
        psim_triggered=psim_triggered,
        irgm_triggered=irgm_triggered,
        session_terminated=(
            decision == "reject"
            or s.phase == NegotiationPhase.TERMINATED
        ),
    )
    s._last_result = result
    return result


def _accept_result(
    s: NegotiationState,
    price: float,
    tag: ReasoningTag,
) -> EngineResult:
    # Patch 3: Floor guard — should never be reached, but if it is,
    # log and return a final-offer counter at the floor instead of accepting.
    if price < s.dynamic_floor - 0.01:
        logger.error("accept_below_floor_guard_fired", price=price, floor=s.dynamic_floor)
        s.firmness_level = 3
        return _build_result(s, "counter", s.dynamic_floor, ReasoningTag.BELOW_FLOOR_REJECT)
    return _build_result(s, "accept", price, tag)


def _reject_result(s: NegotiationState, tag: ReasoningTag) -> EngineResult:
    return _build_result(s, "reject", s.dynamic_floor, tag)


def _terminated_result(s: NegotiationState) -> EngineResult:
    s.phase = NegotiationPhase.TERMINATED
    return _build_result(s, "reject", s.dynamic_floor, ReasoningTag.FLOOR_ENFORCED)


def _inquiry_result(s: NegotiationState) -> EngineResult:
    return _build_result(s, "counter", s.bulk_target_price, ReasoningTag.ROUND1_HOLD)


def _stock_exceeded_result(s: NegotiationState, qty: int) -> EngineResult:
    return _build_result(s, "counter", s.base_price, ReasoningTag.FLOOR_ENFORCED)


# ═══════════════════════════════════════════════════════════════════════════════
# QUANTITY-CHANGE RECALCULATION
# ═══════════════════════════════════════════════════════════════════════════════

def _recalculate_for_quantity(s: NegotiationState, old_qty: int) -> None:
    """
    Recalculate derived values when quantity changes mid-negotiation.

    Updates: dynamic_floor (bulk discount), scarcity_locked,
    total_concession_budget, remaining_concession_budget.
    Preserves the fraction of budget already used.
    """
    T = TUNING

    # Recalculate floor (bulk discount depends on quantity)
    s.dynamic_floor = _compute_dynamic_floor(s)
    s.dynamic_floor = _apply_psim(s)

    # Recalculate bulk target price
    s.bulk_target_price = max(
        compute_bulk_target_price(s.base_price, s.quantity, s.mode),
        s.dynamic_floor,
    )

    # ── Quantity change: always reset counters and firmness state ──
    #   The deal fundamentally changed — old counters don't reflect
    #   the correct bulk discount for the new quantity (Bug 7 fix).
    s.firmness_level = 0
    s.consecutive_stagnant = 0
    s.retrograde_count = 0

    # Always clear on quantity change (Bug 7)
    s.counter_history.clear()
    s.offer_history.clear()
    rounds_remaining = max(s.max_rounds - s.current_round, 2)
    s.max_rounds = rounds_remaining
    s.current_round = 0

    # Recalculate scarcity lock
    s.scarcity_locked = (
        (s.available_inventory - s.quantity) < T["scarcity_stock_threshold"]
    )
    if s.scarcity_locked:
        s.dynamic_floor = round(
            min(s.dynamic_floor * (1 + T["scarcity_floor_lift"]), s.base_price),
            2,
        )

    # Scale concession budget (full reset on any qty change)
    qty_changed = s.quantity != old_qty
    # Full budget reset on qty change (function only called when qty differs)
    new_budget = max((s.base_price - s.dynamic_floor) * s.quantity, 0.0)
    s.total_concession_budget = new_budget
    s.remaining_concession_budget = new_budget

# ═══════════════════════════════════════════════════════════════════════════════
# GRADUATED FIRMNESS  (replaces binary freeze / final_offer_issued)
# ═══════════════════════════════════════════════════════════════════════════════

def _update_firmness(state: NegotiationState, u_price: float) -> None:
    """
    Update firmness_level based on buyer's latest move.
    Called in process_round after offer_history is updated.
    """
    if len(state.offer_history) < 2:
        return  # First offer — no history to compare, firmness stays 0

    prev_offer = state.offer_history[-2]
    move = u_price - prev_offer
    move_pct = move / state.base_price if state.base_price > 0 else 0

    T = TUNING

    if move < 0:
        # Retrograde — buyer went backwards
        state.firmness_level = min(3, state.firmness_level + 1)
    elif move == 0:
        # Stagnation — identical offer
        state.firmness_level = min(3, state.firmness_level + 1)
    else:
        # Buyer moved forward
        if move_pct >= T["firmness_large_move_pct"]:
            state.firmness_level = max(0, state.firmness_level - 2)
        elif move_pct >= T["firmness_good_move_pct"]:
            state.firmness_level = max(0, state.firmness_level - 1)
        # Small upward move (< 2% of base): no firmness change
        # Buyer is grinding, not punished but not rewarded either

    # Proximity override: if buyer is genuinely close, full reset regardless
    if state.counter_history:
        last_ctr = state.counter_history[-1]
        if last_ctr > 0 and u_price >= last_ctr * T["fair_offer_proximity_ratio"]:
            state.firmness_level = 0


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENGINE — process_round  (the ONLY public entry point)
# ═══════════════════════════════════════════════════════════════════════════════

def process_round(state: NegotiationState, extraction: dict) -> EngineResult:
    """
    Pure function. No I/O. No LLM calls. No randomness.
    Mutates state in-place (state is the persistent session object
    held in TTLCache). Returns a frozen, immutable EngineResult.

    Key invariant: BBI and WTP update on EVERY round that has a
    numeric offer, even when the buyer's price is below the dynamic
    floor.  This keeps state tracking accurate across all rounds.
    """

    # ── STEP 0: Normalize prices from extraction ──────────────
    qty = extraction.get("quantity") or state.quantity
    old_qty = state.quantity

    if qty != old_qty:
        # Quantity changed mid-negotiation — recalculate derived values
        state.quantity = qty
        _recalculate_for_quantity(state, old_qty)
    else:
        state.quantity = qty

    u_price = extraction.get("unit_price_offered")
    t_price = extraction.get("total_price_offered")

    if u_price is None and t_price is not None:
        u_price = round(t_price / qty, 2)
    elif u_price is not None and t_price is None:
        t_price = round(u_price * qty, 2)
    elif u_price is None and t_price is None:
        # Pure inquiry — no offer made
        return _inquiry_result(state)

    # ── Sanity: cap per-unit price at base_price ──────────────
    #   A buyer offering above the seller's asking price is almost
    #   certainly a mistype or parsing error. Treat it as offering
    #   exactly base_price (the maximum the seller would expect).
    if u_price > state.base_price:
        u_price = state.base_price
        t_price = round(u_price * qty, 2)

    extraction["resolved_unit_price"] = u_price

    # ── STEP 1: Quantity validation ───────────────────────────
    if qty > state.available_inventory:
        return _stock_exceeded_result(state, qty)

    # ── STEP 2: Advance round ─────────────────────────────────
    state.current_round += 1
    state.offer_history.append(u_price)

    # Store buyer's raw message for verbalize context (Patch 3)
    if extraction.get("raw_message"):
        state._last_buyer_message = extraction["raw_message"]

    # ── STEP 2.5: Update firmness ─────────────────────────────
    #   Must run AFTER offer_history is updated, BEFORE any other
    #   computation.  This is the graduated firmness system.
    _update_firmness(state, u_price)

    # ── STEP 3: Update phase ──────────────────────────────────
    state.phase = _determine_phase(state)

    # ── STEP 4: Intent shortcuts ──────────────────────────────
    if extraction.get("intent") == "accept":
        last_counter = state.counter_history[-1] if state.counter_history else state.bulk_target_price
        return _accept_result(state, last_counter, ReasoningTag.UTILITY_ACCEPT)

    if extraction.get("intent") == "walkaway":
        return _terminated_result(state)

    # ── STEP 5: Update BBI (ALWAYS — tracks buyer behavior) ──
    state.bbi, bbi_tag = _update_bbi(state, extraction)

    # ── STEP 5.5: Re-determine phase (firmness may have changed) ──
    state.phase = _determine_phase(state)

    # ── STEP 6: Update Bayesian WTP (ALWAYS) ──────────────────
    state.p_high_wtp = _update_wtp(state)

    # ── STEP 7: Anti-manipulation ─────────────────────────────
    #   Now runs AFTER BBI update, so retrograde_count and
    #   consecutive_stagnant reflect the current round.
    manip_tag = _check_manipulation(state, extraction)
    if manip_tag in (ReasoningTag.STAGNATION_FINAL, ReasoningTag.RETROGRADE_FINAL):
        last = state.counter_history[-1] if state.counter_history else state.dynamic_floor
        state.counter_history.append(last)
        return _build_result(state, "final_offer", last, manip_tag)
    if manip_tag in (ReasoningTag.BUNDLE_DEFLECT, ReasoningTag.SOCIAL_PROOF_RESIST):
        last = state.counter_history[-1] if state.counter_history else state.bulk_target_price
        return _build_result(state, "counter", last, manip_tag)

    # ── (STEP 7.5 REMOVED: old frozen-counter shortcut is gone) ──
    #   Graduated firmness handles concession reduction via multiplier.

    # ── STEP 8: ZOPA check ────────────────────────────────────
    #   Only count no-overlap rounds AFTER the anchor-resist phase.
    #   Early lowballs are normal tactics, not proof of no overlap.
    buyer_ceiling = _extrapolate_buyer_ceiling(state)
    meaningful_overlap = buyer_ceiling >= state.dynamic_floor + (0.01 * state.base_price)
    if state.phase != NegotiationPhase.ANCHOR_RESIST:
        if not meaningful_overlap:
            state.zopa_no_overlap_count += 1
        else:
            state.zopa_no_overlap_count = 0

    if state.zopa_no_overlap_count >= TUNING["zopa_no_overlap_max_rounds"]:
        state.firmness_level = 3
        # Use last counter, not floor — jumping to floor is an
        # unearned gift to the buyer.  Signal firmness by holding
        # at the current negotiation position.
        anchor = (
            state.counter_history[-1]
            if state.counter_history
            else state.bulk_target_price
        )
        state.counter_history.append(anchor)
        return _build_result(
            state, "final_offer", anchor,
            ReasoningTag.ZOPA_NO_OVERLAP, buyer_ceiling,
        )

    # ── STEP 8.5: Acceptance check (before round exhaustion) ───
    #   Patch 3 Bug B Fix 2: run acceptance BEFORE max-rounds
    #   termination so valid last-round offers aren't auto-rejected.
    if u_price >= state.dynamic_floor and _should_accept(
        state, u_price,
        state.counter_history[-1] if state.counter_history else state.bulk_target_price,
    ):
        return _accept_result(state, u_price, ReasoningTag.UTILITY_ACCEPT)

    # ── STEP 9: Last round ───────────────────────────────────
    #   Accept only if the offer is close to the last counter.
    #   Blindly accepting anything above floor lets a buyer who
    #   negotiated nowhere near our price grab a huge discount.
    if state.current_round >= state.max_rounds:
        last_counter = (
            state.counter_history[-1]
            if state.counter_history
            else state.bulk_target_price
        )
        min_accept = last_counter * TUNING["last_round_min_counter_ratio"]
        if u_price >= min_accept:
            return _accept_result(state, u_price, ReasoningTag.LAST_ROUND_ACCEPT)
        return _reject_result(state, ReasoningTag.LAST_ROUND_REJECT)

    # ── STEP 10: Compute counter-price ────────────────────────
    #   _compute_concession always clamps at dynamic_floor,
    #   so below-floor offers naturally produce a high counter
    #   from the concession curve rather than jumping to floor.
    counter_price, concession_tag = _compute_concession(state, u_price)

    # ── STEP 10.1: Counter ratchet — never reward retrograde ──
    #   Rule 1: If buyer went BELOW their previous offer or is at/
    #   below their all-time best, HOLD the counter.  Never raise
    #   the counter above the last counter — the seller asking for
    #   MORE than they already offered looks absurd to the buyer.
    #   Rule 2: If buyer set a new personal best, normal concession.
    #   Budget is restored for the phantom concession so the seller
    #   doesn't lose negotiating power from the buyer's bad moves.
    if state.counter_history and len(state.offer_history) >= 2:
        prev_counter = state.counter_history[-1]
        current_offer = state.offer_history[-1]
        buyer_prev_best = max(state.offer_history[:-1])

        if current_offer <= buyer_prev_best:
            # At or below all-time best (includes retrograde)
            # → hold counter, never concede for free
            floor_price = prev_counter
        else:
            floor_price = None  # buyer beat their best — allow concession

        if floor_price is not None and counter_price < floor_price:
            leaked = (floor_price - counter_price) * state.quantity
            state.remaining_concession_budget = min(
                state.remaining_concession_budget + leaked,
                state.total_concession_budget,
            )
            counter_price = floor_price

    # ── STEP 10.2: Hard ratchet — counter can NEVER exceed lowest historical ──
    #   Extra safety net: even if concession math somehow produces a
    #   counter above a previously issued counter, clamp it down.
    if state.counter_history:
        historical_min = min(state.counter_history)
        if counter_price > historical_min:
            leaked = (counter_price - historical_min) * state.quantity
            state.remaining_concession_budget = min(
                state.remaining_concession_budget + leaked,
                state.total_concession_budget,
            )
            counter_price = historical_min

    state.counter_history.append(counter_price)

    # Track whether concession was effectively zero (for decision type)
    last_counter_before = state.counter_history[-2] if len(state.counter_history) >= 2 else state.bulk_target_price
    concession_step_zero = abs(counter_price - last_counter_before) < 0.005

    # ── STEP 10.5: Auto-accept if buyer meets or exceeds counter ──
    #   No point countering lower than what the buyer already offered.
    if u_price >= counter_price:
        return _accept_result(state, u_price, ReasoningTag.EXTENDED_UTILITY)

    # ── STEP 11: Extended utility acceptance check ────────────
    #   Only consider accepting when offer >= floor.
    if u_price >= state.dynamic_floor and _should_accept(state, u_price, counter_price):
        return _accept_result(state, u_price, ReasoningTag.EXTENDED_UTILITY)

    # ── STEP 12: Select final reasoning tag ───────────────────
    below_floor = u_price < state.dynamic_floor
    if below_floor:
        final_tag = bbi_tag or ReasoningTag.BELOW_FLOOR_REJECT
    elif state.p_high_wtp > 0.70:
        final_tag = ReasoningTag.BAYESIAN_HOLD
    else:
        final_tag = bbi_tag or concession_tag

    # ── STEP 12.5: Decision type based on firmness ────────────
    #   firmness_level == 3 with zero concession → final_offer
    #   Otherwise → counter
    if concession_step_zero or state.firmness_level == 3:
        decision_type = "final_offer"
    else:
        decision_type = "counter"

    # ── STEP 13: Safety invariants ─────────────────────────────
    #   Use explicit checks (not assert) so they survive python -O.
    if counter_price < state.dynamic_floor - 0.01:
        raise RuntimeError(
            f"VIOLATION: counter {counter_price:.2f} below floor {state.dynamic_floor:.2f}"
        )
    if counter_price < state.cost_price - 0.01:
        raise RuntimeError(
            f"VIOLATION: counter {counter_price:.2f} below cost {state.cost_price:.2f}"
        )
    if counter_price > state.base_price + 0.01:
        raise RuntimeError(
            f"VIOLATION: counter {counter_price:.2f} above base {state.base_price:.2f}"
        )
    if state.remaining_concession_budget < -0.01:
        raise RuntimeError(
            f"VIOLATION: budget negative {state.remaining_concession_budget:.2f}"
        )

    return _build_result(state, decision_type, counter_price, final_tag, buyer_ceiling)
