"""
Negotiation Engine - Pydantic Schemas

Strict validation models for all API inputs and outputs.
These schemas enforce seller constraints are never violated.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID, uuid4
import html as _html

from .enums import (
    NegotiationMode,
    PressureLevel,
    FrequencyLevel,
    UrgencyLevel,
    RelationshipPriority,
    NegotiationStatus,
    OfferDecision,
)


# =============================================================================
# INPUT SCHEMAS (Seller-Defined, Immutable)
# =============================================================================

class ProductData(BaseModel):
    """Product and cost information - immutable during negotiation."""
    
    product_id: str = Field(..., min_length=1, max_length=100, description="Unique product identifier")
    product_name: str = Field(..., min_length=1, max_length=200, description="Product display name")
    base_price: Decimal = Field(..., gt=0, le=Decimal("99999999.99"), description="Listed/base price per unit")
    cost_price: Decimal = Field(..., gt=0, le=Decimal("99999999.99"), description="Cost per unit to seller")
    min_acceptable_price: Decimal = Field(..., gt=0, le=Decimal("99999999.99"), description="Absolute floor price")
    max_loss_percentage: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=100,
        description="Maximum allowed loss % (only in MIN_LOSS mode)"
    )
    
    @model_validator(mode="after")
    def validate_price_hierarchy(self):
        """Ensure price hierarchy is logical."""
        if self.min_acceptable_price > self.base_price:
            raise ValueError("min_acceptable_price cannot exceed base_price")
        if self.cost_price > self.base_price:
            raise ValueError("cost_price cannot exceed base_price (negative margin)")
        if self.min_acceptable_price < self.cost_price:
            raise ValueError("min_acceptable_price cannot be below cost_price (would allow selling at a loss)")
        return self


class InventoryContext(BaseModel):
    """Inventory and sales context - affects pricing flexibility."""
    
    available_quantity: int = Field(..., gt=0, description="Units available in stock")
    requested_quantity: int = Field(..., gt=0, description="Units buyer wants")
    inventory_pressure: PressureLevel = Field(
        default=PressureLevel.MEDIUM,
        description="How urgently we need to move inventory"
    )
    sales_frequency: FrequencyLevel = Field(
        default=FrequencyLevel.MEDIUM,
        description="How often this product sells"
    )
    
    @model_validator(mode="after")
    def validate_quantity(self):
        """Requested cannot exceed available."""
        if self.requested_quantity > self.available_quantity:
            raise ValueError("requested_quantity cannot exceed available_quantity")
        return self


class StrategicControls(BaseModel):
    """Seller's strategic settings - controls negotiation behavior."""
    
    mode: NegotiationMode = Field(
        default=NegotiationMode.MAX_PROFIT,
        description="Operating mode: MAX_PROFIT or MIN_LOSS"
    )
    urgency: UrgencyLevel = Field(
        default=UrgencyLevel.MEDIUM,
        description="Seller urgency to close deal"
    )
    relationship_priority: RelationshipPriority = Field(
        default=RelationshipPriority.MEDIUM,
        description="Importance of buyer relationship"
    )
    max_rounds: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum negotiation rounds before walk-away"
    )


class CreateSessionRequest(BaseModel):
    """Request to create a new negotiation session."""
    
    product: ProductData
    inventory: InventoryContext
    strategy: StrategicControls = Field(default_factory=StrategicControls)
    buyer_id: Optional[str] = Field(default=None, description="Optional buyer identifier")
    metadata: Optional[dict] = Field(default=None, description="Custom metadata")


# =============================================================================
# NEGOTIATION TURN SCHEMAS
# =============================================================================

class BuyerOffer(BaseModel):
    """A buyer's offer in the negotiation."""
    
    offered_price: Decimal = Field(..., gt=0, le=Decimal("99999999.99"), description="Buyer's offered price per unit")
    offered_quantity: Optional[int] = Field(
        default=None,
        gt=0,
        description="Buyer may request different quantity"
    )
    message: Optional[str] = Field(default=None, max_length=1000, description="Buyer's message")


class ChatMessage(BaseModel):
    """Free-text chat message from the buyer (may or may not contain a price)."""
    
    message: str = Field(..., min_length=1, max_length=2000, description="Buyer's free-text message")


class ChatResponse(BaseModel):
    """Response to a chat message."""
    
    session_id: UUID
    message: str
    has_price_offer: bool = False
    extracted_price: Optional[Decimal] = None
    
    # If a price was found, these are populated (same as NegotiationTurnResponse)
    round_number: Optional[int] = None
    status: Optional[NegotiationStatus] = None
    pricing: Optional["PricingDecision"] = None
    can_continue: Optional[bool] = None
    rounds_remaining: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NegotiationTurnRequest(BaseModel):
    """Request to process a negotiation turn."""
    
    session_id: UUID
    buyer_offer: BuyerOffer


# =============================================================================
# OUTPUT SCHEMAS
# =============================================================================

class PricingDecision(BaseModel):
    """Deterministic pricing decision from the Pricing Strategy Agent."""
    
    decision: OfferDecision
    counter_offer_price: Optional[Decimal] = None
    accepted_price: Optional[Decimal] = None
    
    # Computed metrics
    margin_percentage: Decimal
    profit_per_unit: Decimal
    total_profit: Decimal
    
    # Constraint status
    within_constraints: bool
    constraint_violations: List[str] = Field(default_factory=list)
    
    # Concession tracking
    concession_made: Decimal = Field(default=Decimal("0"))
    remaining_concession_budget: Decimal
    concession_percentage_used: Decimal


class NegotiationTurnResponse(BaseModel):
    """Response for a single negotiation turn."""
    
    session_id: UUID
    round_number: int
    status: NegotiationStatus
    
    # Pricing decision
    pricing: PricingDecision
    
    # Conversation output
    message: str
    
    # Session state
    can_continue: bool
    rounds_remaining: int
    
    # Audit trail
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionSummary(BaseModel):
    """Summary of a completed or active negotiation session."""
    
    session_id: UUID
    status: NegotiationStatus
    mode: NegotiationMode
    
    # Price journey
    initial_offer_price: Decimal
    final_price: Optional[Decimal]
    
    # Outcome metrics
    rounds_taken: int
    total_profit: Optional[Decimal]
    profit_margin_percentage: Optional[Decimal]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]


class CreateSessionResponse(BaseModel):
    """Response after creating a new negotiation session."""
    
    session_id: UUID
    initial_offer: Decimal
    message: str
    max_rounds: int
    mode: NegotiationMode
    created_at: datetime


# =============================================================================
# ANALYTICS SCHEMAS
# =============================================================================

class NegotiationAnalytics(BaseModel):
    """Analytics for a closed negotiation."""
    
    session_id: UUID
    outcome: NegotiationStatus
    
    # Price analysis
    starting_price: Decimal
    final_price: Optional[Decimal]
    buyer_first_offer: Decimal
    total_concession_given: Decimal
    concession_percentage: Decimal
    
    # Performance
    rounds_used: int
    rounds_available: int
    efficiency_score: Decimal  # How quickly deal closed vs max rounds
    
    # Profit analysis
    gross_profit: Optional[Decimal]
    profit_margin: Optional[Decimal]
    mode_used: NegotiationMode
    
    # Audit
    constraint_violations_attempted: int
    walk_away_triggered: bool
