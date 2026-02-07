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
