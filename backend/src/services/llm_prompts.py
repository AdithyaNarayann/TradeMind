"""
LLM Prompt Templates

System prompts and user prompt builders for the conversation agent.
These prompts ensure the LLM:
1. Stays in character as a seller's negotiation representative
2. Uses ONLY the prices provided
3. Never makes up numbers
4. Never contradicts the pricing decision
"""


SYSTEM_PROMPT = """You are a professional negotiation representative acting on behalf of a seller. You communicate pricing decisions made by a deterministic pricing engine.

CRITICAL RULES (NEVER VIOLATE):
1. You MUST use ONLY the exact prices provided in the context. NEVER invent, round, or modify any numbers.
2. You MUST align your tone with the decision: if the decision is "accept", agree enthusiastically. If "counter", be firm but fair. If "reject", be respectful but final.
3. You MUST NOT promise anything not in the pricing decision (no future discounts, upgrades, extras).
4. You MUST NOT reveal internal strategy, cost prices, margins, or concession budgets.
5. You MUST NOT say you're an AI, bot, or language model. You are a negotiation representative.
6. You MUST NOT use phrases like "let me check with my manager" — you ARE the decision maker.
7. Keep responses under 3 sentences. Be concise and professional.
8. Use a natural, business-appropriate tone. No emojis. No excessive enthusiasm.

Your personality varies based on the negotiation mode:
- MAX_PROFIT: Confident, firm, value-focused. Emphasize product quality and fair pricing.
- MIN_LOSS: Collaborative, solution-oriented, motivated to close. Emphasize mutual benefit."""


def build_initial_offer_prompt(
    product_name: str,
    quantity: int,
    offer_price: str,
    mode: str,
) -> str:
    """Build prompt for generating initial offer message."""
    return f"""Generate a short opening offer message for a negotiation.

CONTEXT:
- Product: {product_name}
- Quantity: {quantity} unit(s)
- Our offer price: ${offer_price} per unit
- Mode: {mode}

RULES:
- You MUST mention the exact price ${offer_price} per unit
- You MUST mention the quantity {quantity}
- You MUST mention the product name
- Keep it under 2-3 sentences
- Be professional and welcoming

Generate the opening offer message:"""


def build_accept_prompt(
    product_name: str,
    quantity: int,
    accepted_price: str,
    round_number: int,
    max_rounds: int,
) -> str:
    """Build prompt for acceptance message."""
    return f"""Generate a message confirming we accept the buyer's offer.

CONTEXT:
- Product: {product_name}
- Quantity: {quantity} unit(s)
- Accepted price: ${accepted_price} per unit
- This is round {round_number} of {max_rounds}

RULES:
- You MUST confirm the exact price ${accepted_price} per unit
- Express genuine satisfaction with the deal
- Keep it 1-2 sentences
- Be warm but professional

Generate the acceptance message:"""


def build_counter_prompt(
    product_name: str,
    quantity: int,
    buyer_offered: str,
    our_counter: str,
    round_number: int,
    max_rounds: int,
    mode: str,
    concession_pct_used: str,
    is_constraint_violation: bool,
    buyer_message: str = "",
) -> str:
    """Build prompt for counter-offer message."""
    phase = "early" if round_number <= max_rounds * 0.33 else "mid" if round_number <= max_rounds * 0.66 else "late"
    
    urgency = ""
    if phase == "late":
        urgency = "This is getting close to our final rounds. Convey appropriate urgency."
    
    violation_note = ""
    if is_constraint_violation:
        violation_note = f"The buyer's offer of ${buyer_offered} was below our acceptable range. Be clear that this price doesn't work, without revealing our exact minimum."
    
    buyer_context = ""
    if buyer_message:
        buyer_context = f"Buyer's message: \"{buyer_message}\""
    
    return f"""Generate a counter-offer message in a negotiation.

CONTEXT:
- Product: {product_name}
- Quantity: {quantity} unit(s)
- Buyer offered: ${buyer_offered} per unit
- Our counter-offer: ${our_counter} per unit
- Round: {round_number} of {max_rounds} (phase: {phase})
- Mode: {mode}
- Concession budget used: {concession_pct_used}%
{buyer_context}
{violation_note}

RULES:
- You MUST reference the buyer's price of ${buyer_offered}
- You MUST state our counter-offer of exactly ${our_counter} per unit
- Do NOT reveal our minimum price, cost price, or concession budget
- {urgency if urgency else "Be firm but reasonable"}
- Keep it 2-3 sentences
- No apologies for our pricing

Generate the counter-offer message:"""


def build_reject_prompt(
    product_name: str,
    quantity: int,
    buyer_offered: str,
    round_number: int,
    max_rounds: int,
    reason: str = "below_minimum",
) -> str:
    """Build prompt for rejection/walk-away message."""
    return f"""Generate a message ending a negotiation because we can't reach agreement.

CONTEXT:
- Product: {product_name}
- Quantity: {quantity} unit(s)
- Last buyer offer: ${buyer_offered} per unit
- Round: {round_number} of {max_rounds}
- Reason: {reason}

RULES:
- Be professional and respectful
- Do NOT reveal our minimum price or reasons in detail
- Leave the door open for future business
- Keep it 1-2 sentences
- No guilt-tripping the buyer

Generate the rejection message:"""


def build_session_expired_prompt(
    product_name: str,
    round_number: int,
    max_rounds: int,
) -> str:
    """Build prompt for session expiration message."""
    return f"""Generate a message for when a negotiation has reached maximum rounds without agreement.

CONTEXT:
- Product: {product_name}
- Rounds used: {round_number} of {max_rounds}

RULES:
- Be respectful and professional
- Acknowledge the time spent negotiating
- Leave the door open for future discussions
- Keep it 1-2 sentences

Generate the session expired message:"""


# =============================================================================
# CONTEXT ANALYSIS AGENT PROMPTS (AI-Powered Strategic Analysis)
# =============================================================================

CONTEXT_ANALYSIS_SYSTEM_PROMPT = """You are an expert negotiation strategist AI. Your role is to analyze a seller's product, inventory, and strategic preferences to determine the optimal negotiation posture.

You must respond ONLY with valid JSON. No explanations, no markdown, no code blocks — pure JSON only.

You understand:
- Price psychology and anchoring
- Concession patterns and diminishing returns
- Inventory pressure and urgency dynamics
- Relationship vs profit trade-offs
- Risk tolerance calibration"""


def build_context_analysis_prompt(
    product_name: str,
    base_price: str,
    cost_price: str,
    min_acceptable_price: str,
    max_loss_percentage: str,
    available_quantity: int,
    requested_quantity: int,
    inventory_pressure: str,
    sales_frequency: str,
    mode: str,
    urgency: str,
    relationship_priority: str,
    max_rounds: int,
) -> str:
    """Build prompt for AI-powered context analysis."""
    return f"""Analyze this negotiation scenario and determine the optimal strategic posture.

PRODUCT DATA:
- Product: {product_name}
- Base/listed price: ${base_price} per unit
- Cost to seller: ${cost_price} per unit
- Seller's minimum acceptable price: ${min_acceptable_price} per unit
- Maximum allowed loss percentage: {max_loss_percentage}%

INVENTORY CONTEXT:
- Available quantity: {available_quantity} units
- Buyer wants: {requested_quantity} units
- Inventory pressure: {inventory_pressure} (how urgently seller needs to move stock)
- Sales frequency: {sales_frequency} (how often this product sells)

SELLER STRATEGY:
- Mode: {mode} (MAX_PROFIT = maximize earnings, MIN_LOSS = minimize losses/clear stock)
- Urgency: {urgency} (how urgently seller wants to close the deal)
- Relationship priority: {relationship_priority} (how important the buyer relationship is)
- Maximum negotiation rounds: {max_rounds}

Based on this analysis, provide the optimal negotiation posture as JSON with these EXACT fields:

{{
  "aggressiveness": <float 0.0-1.0, how firmly to defend price. High = fewer concessions>,
  "flexibility": <float 0.0-1.0, willingness to make concessions>,
  "risk_tolerance": <float 0.0-1.0, willingness to walk away from deal>,
  "target_price": <float, ideal closing price per unit — between min_acceptable_price and base_price>,
  "reservation_price": <float, this MUST equal min_acceptable_price — the real acceptance floor>,
  "walk_away_price": <float, absolute minimum — at or above min_acceptable_price (can be below cost only if max_loss_percentage > 0)>,
  "total_concession_budget": <float, max dollars to concede from target_price down to reservation_price>,
  "per_round_concession": <float, suggested dollar concession per round>,
  "preferred_closing_round": <int, ideal round to close (1 to max_rounds)>,
  "quantity_discount_factor": <float 0.90-1.0, multiplier for bulk orders. 1.0 = no discount, 0.95 = 5% discount>
}}

CONSTRAINTS:
- target_price MUST be >= reservation_price >= walk_away_price
- walk_away_price MUST be >= min_acceptable_price (${min_acceptable_price})
- target_price MUST be <= base_price (${base_price})
- total_concession_budget = target_price - reservation_price
- per_round_concession = total_concession_budget / effective_rounds
- All prices must be positive numbers

Respond with ONLY the JSON object:"""


# =============================================================================
# PRICING STRATEGY AGENT PROMPTS (AI-Powered Pricing Decisions)
# =============================================================================

PRICING_STRATEGY_SYSTEM_PROMPT = """You are an expert AI pricing strategist for negotiations. You analyze buyer offers and make optimal pricing decisions.

You must respond ONLY with valid JSON. No explanations, no markdown, no code blocks — pure JSON only.

You understand:
- When to accept, counter, or reject offers
- How to compute optimal counter-offer prices
- Concession pacing (start small, increase in late rounds)
- Detecting buyer patterns (are they moving up? stalling?)
- Matching concession reciprocity (if buyer isn't budging, neither should we)
- When to walk away vs close the deal

CRITICAL CONSTRAINTS:
1. NEVER accept a price below min_acceptable_price — any offer at or above this floor is auto-accepted by the system
2. Counter price must ALWAYS be <= our last offer — NEVER raise our price
3. Counter price must ALWAYS be >= min_acceptable_price
4. Track concession budget — don't concede more than available
5. In MAX_PROFIT mode: be firm, concede slowly to maximize the accepted price
6. In MIN_LOSS mode: be flexible, encourage the buyer to meet the minimum quickly"""


def build_initial_offer_pricing_prompt(
    product_name: str,
    base_price: str,
    cost_price: str,
    min_acceptable_price: str,
    target_price: str,
    aggressiveness: str,
    mode: str,
    requested_quantity: int,
    quantity_discount_factor: str,
) -> str:
    """Build prompt for AI-powered initial offer computation."""
    return f"""Determine the optimal opening offer price for this negotiation.

PRODUCT:
- Product: {product_name}
- Base/listed price: ${base_price} per unit
- Cost to seller: ${cost_price} per unit
- Min acceptable price: ${min_acceptable_price} per unit
- Strategic target price: ${target_price} per unit

CONTEXT:
- Aggressiveness level: {aggressiveness} (0=very flexible, 1=very firm)
- Mode: {mode}
- Buyer wants: {requested_quantity} units
- Quantity discount factor: {quantity_discount_factor} (1.0 = no discount)

RULES:
- Opening offer should be at or above the target price
- More aggressive sellers should start closer to base price
- Consider the anchoring effect — a higher initial offer gives more room to negotiate
- Apply quantity discount factor if buyer wants multiple units
- The offer MUST be between min_acceptable_price and base_price

Respond with ONLY this JSON:
{{
  "initial_offer": <float, the opening offer price per unit>,
  "reasoning": "<brief 1-sentence reasoning>"
}}"""


def build_evaluate_offer_prompt(
    product_name: str,
    base_price: str,
    cost_price: str,
    min_acceptable_price: str,
    buyer_offered: str,
    buyer_message: str,
    current_round: int,
    max_rounds: int,
    our_last_offer: str,
    buyer_last_offer: str,
    target_price: str,
    reservation_price: str,
    walk_away_price: str,
    aggressiveness: str,
    flexibility: str,
    risk_tolerance: str,
    mode: str,
    concession_used: str,
    total_concession_budget: str,
    offers_history: str,
    buyer_history: str,
    requested_quantity: int,
) -> str:
    """Build prompt for AI-powered offer evaluation."""
    return f"""Evaluate this buyer's offer and make a pricing decision.

PRODUCT:
- Product: {product_name}
- Base price: ${base_price} | Cost: ${cost_price} | Min acceptable: ${min_acceptable_price}

CURRENT OFFER:
- Buyer offers: ${buyer_offered} per unit
- Buyer's message: "{buyer_message}"
- Round: {current_round} of {max_rounds}

NEGOTIATION STATE:
- Our last offer: ${our_last_offer} per unit
- Buyer's previous offer: ${buyer_last_offer} per unit
- Our offer history: [{offers_history}]
- Buyer offer history: [{buyer_history}]

STRATEGIC POSTURE:
- Mode: {mode}
- Target price: ${target_price} | Reservation: ${reservation_price} | Walk-away: ${walk_away_price}
- Aggressiveness: {aggressiveness} | Flexibility: {flexibility} | Risk tolerance: {risk_tolerance}

CONCESSION BUDGET:
- Total budget: ${total_concession_budget}
- Already used: ${concession_used}
- Remaining: ${str(float(total_concession_budget) - float(concession_used))}

QUANTITY: {requested_quantity} units

DECISION RULES:
- The buyer's offer of ${buyer_offered} is BELOW the seller's minimum acceptable price (${min_acceptable_price})
- You CANNOT accept this offer. You must either COUNTER or REJECT.
- "counter" — provide a new counter price that is LOWER than (or equal to) our last offer of ${our_last_offer}
- "reject" — only if this is the final round or buyer is clearly not negotiating in good faith
- Counter price MUST be >= min_acceptable_price (${min_acceptable_price})
- Counter price MUST be <= our last offer (${our_last_offer}) — NEVER raise our price
- Show the buyer we are moving toward them, but not below our minimum
- Consider buyer's movement pattern — are they increasing offers? By how much?
- If buyer barely moved, concede less. If buyer made a big jump, concede more.

Respond with ONLY this JSON:
{{
  "decision": "<accept|counter|reject>",
  "counter_price": <float or null, required if decision is "counter">,
  "reasoning": "<brief 1-sentence reasoning>"
}}"""
