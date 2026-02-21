"""
Negotiation Engine - Core Type Definitions

All enums, literals, and shared types used across the system.
These types enforce the seller-defined constraints at compile time.
"""
from enum import Enum
from typing import Literal


class NegotiationMode(str, Enum):
    """Operating mode for the negotiation engine."""
    MAX_PROFIT = "MAX_PROFIT"  # Maximize seller profit
    MIN_LOSS = "MIN_LOSS"      # Minimize seller loss


class PressureLevel(str, Enum):
    """Inventory or time pressure levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FrequencyLevel(str, Enum):
    """Sales frequency for the product."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UrgencyLevel(str, Enum):
    """Seller's urgency to close the deal."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RelationshipPriority(str, Enum):
    """Priority given to buyer relationship."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NegotiationStatus(str, Enum):
    """Current status of a negotiation session."""
    ACTIVE = "active"
    ACCEPTED = "accepted"           # Buyer accepted offer
    REJECTED = "rejected"           # Seller walked away
    EXPIRED = "expired"             # Max rounds reached
    BUYER_WALKED = "buyer_walked"   # Buyer ended negotiation


class OfferDecision(str, Enum):
    """Decision made on a buyer's offer."""
    ACCEPT = "accept"           # Accept buyer's offer
    COUNTER = "counter"         # Make a counter-offer
    REJECT = "reject"           # Reject and end negotiation
    HOLD = "hold"               # Need more information
