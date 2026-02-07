import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, Integer, NUMERIC, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database.base import Base


class NegotiationMode(str, enum.Enum):
    MAX_PROFIT = "MAX_PROFIT"
    MIN_LOSS = "MIN_LOSS"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    BUYER_WALKED = "buyer_walked"


class NegotiationSession(Base):
    __tablename__ = "negotiation_sessions"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    # Foreign Key → User (seller)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Strategy
    mode = Column(Enum(NegotiationMode), nullable=False, index=True)
    status = Column(Enum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE, index=True)

    # Product Details (copied at session start)
    product_id = Column(String(100), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100), nullable=True)
    product_category = Column(String(100), nullable=True)

    # Strategy Inputs
    urgency = Column(String(50), nullable=True)
    inventory_pressure = Column(String(50), nullable=True)
    relationship_priority = Column(String(50), nullable=True)

    # Round Tracking
    max_rounds = Column(Integer, nullable=False)
    rounds_taken = Column(Integer, nullable=False, default=0)

    # Pricing
    initial_offer_price = Column(NUMERIC(19, 4), nullable=False)
    final_price = Column(NUMERIC(19, 4), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
    turns = relationship("NegotiationTurn", back_populates="session", cascade="all, delete-orphan")
    analytics = relationship("SessionAnalytics", back_populates="session", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_sessions_user_id_status", "user_id", "status"),
        Index("ix_sessions_status_created", "status", "created_at"),
    )
