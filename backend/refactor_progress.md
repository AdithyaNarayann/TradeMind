# TradeMind Patch 2 — Refactor Progress

**Status:** ✅ Complete  
**Last updated:** 2026-06-08T15:30 — all files complete  

## Files

| File | Status | Bugs/Upgrades Covered |
|------|--------|----------------------|
| negotiation_engine.py | ✅ Done | Graduated firmness, Bug C, TUNING |
| engine.py | ✅ Done | Bug A, Bug B, Bug E, Bug F, Bug H |
| pricing_agent.py | ✅ Done | Bug F fallback, verbalize firmness context |
| prompt_templates.py | ✅ Done | Bug A extraction, Bug D total price, Bug E negative |

## Tasks

- [x] Create refactor_progress.md
- [x] Write negotiation_engine.py
- [x] Write engine.py
- [x] Write pricing_agent.py
- [x] Write prompt_templates.py
- [x] Write completion summary

## Completion Summary

### Per-Bug/Upgrade Summary

| Bug/Upgrade | What was implemented | Where |
|-------------|---------------------|-------|
| **Part 1: Graduated Firmness** | Replaced `final_offer_issued: bool` with `firmness_level: int` (0-3). New `_update_firmness()` function. Firmness multipliers `[1.0, 0.50, 0.15, 0.0]` gate concession. | `negotiation_engine.py` |
| **Bug A** | `QUANTITY_SENTENCE_RE` guard on bare-regex fallback prevents qty numbers as prices. LLM system prompt tells LLM not to extract qty as price. | `engine.py`, `prompt_templates.py` |
| **Bug B** | Zombie pending-confirmation cleanup at top of `process_chat()`. If buyer sends non-accept after confirmation prompt, stale context is logged and cleared. | `engine.py` |
| **Bug C** | Restored `min_acceptance_ratio_max_profit = 0.88` (hard floor). Removed fair-engagement acceptance relaxation. | `negotiation_engine.py` |
| **Bug D** | Added "ADDITIONAL TOTAL INDICATORS" to LLM prompt: "for both/all/lot" → always total; price > base but ≤ base×qty×1.1 → likely total. | `prompt_templates.py` |
| **Bug E** | `NEGATIVE_RE` + `BARE_NO_RE` routing in fallback path. "no"/"nope"/"too expensive" → invite new price offer instead of generic reply. LLM system prompt tells LLM to set `accepts_deal=false`. | `engine.py`, `prompt_templates.py` |
| **Bug F** | Diagnostic `logger.warning()` in `process_turn()` when `_last_result` is None. `_FIRMNESS_FALLBACKS` dict for template fallback. `firmness_level` + `buyer_moving_up` passed to verbalizer prompt. | `engine.py`, `pricing_agent.py` |
| **Bug G** | Covered by Part 1 (graduated firmness replaces binary freeze). | `negotiation_engine.py` |
| **Bug H** | Generic no-price fallback reply now uses engine counter history, mentions total for multi-qty, and records exchange in `chat_history`. | `engine.py` |
| **Firmness in `_apply_quantity_change`** | Replaced `final_offer_issued = False` with `firmness_level = 0`. Removed obsolete freeze fields (`good_faith_after_final`, `_freeze_low_offer`, etc.). | `engine.py` |
