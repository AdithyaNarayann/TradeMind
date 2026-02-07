import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, Integer, Boolean, NUMERIC, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database.base import Base


class TurnDecision(str, enum.Enum):
    ACCEPT = "accept"
    COUNTER = "counter"
    REJECT = "reject"
    HOLD = "hold"


class NegotiationTurn(Base):
    __tablename__ = "negotiation_turns"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    # Foreign Key → Session
    session_id = Column(UUID(as_uuid=True), ForeignKey("negotiation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Round Tracking
    round_number = Column(Integer, nullable=False)

    # Buyer Input
    buyer_offered_price = Column(NUMERIC(19, 4), nullable=False)
    buyer_offered_quantity = Column(Integer, nullable=True)
    buyer_message = Column(String(1000), nullable=True)

    # Seller Decision
    decision = Column(Enum(TurnDecision), nullable=False, index=True)
    counter_offer_price = Column(NUMERIC(19, 4), nullable=True)
    accepted_price = Column(NUMERIC(19, 4), nullable=True)

    # Concession Tracking
    concession_made = Column(NUMERIC(19, 4), nullable=True)
    remaining_concession_budget = Column(NUMERIC(19, 4), nullable=True)

    # Profitability Snapshot
    margin_percentage = Column(NUMERIC(7, 4), nullable=True)
    profit_per_unit = Column(NUMERIC(19, 4), nullable=True)
    total_profit = Column(NUMERIC(19, 4), nullable=True)

    # Constraint Tracking
    within_constraints = Column(Boolean, nullable=False, default=True)
    constraint_violations = Column(JSONB, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    session = relationship("NegotiationSession", back_populates="turns")

    __table_args__ = (
        Index("ix_turns_session_round", "session_id", "round_number"),
    )
