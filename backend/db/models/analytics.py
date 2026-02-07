from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Boolean, NUMERIC, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database.base import Base


class SessionAnalytics(Base):
    __tablename__ = "session_analytics"

    # Primary Key + Foreign Key → Session (1:1)
    session_id = Column(UUID(as_uuid=True), ForeignKey("negotiation_sessions.id", ondelete="CASCADE"), primary_key=True, nullable=False)

    # Buyer First Move
    buyer_first_offer = Column(NUMERIC(19, 4), nullable=True)

    # Concession Analysis
    total_concession_given = Column(NUMERIC(19, 4), nullable=True)
    concession_percentage = Column(NUMERIC(7, 4), nullable=True)

    # Round Usage
    rounds_used = Column(Integer, nullable=False, default=0)
    rounds_available = Column(Integer, nullable=False)

    # Efficiency & Profitability
    efficiency_score = Column(NUMERIC(7, 4), nullable=True)
    gross_profit = Column(NUMERIC(19, 4), nullable=True)
    profit_margin = Column(NUMERIC(7, 4), nullable=True)

    # Constraint & Walk-Away
    constraint_violations_attempted = Column(Integer, nullable=False, default=0)
    walk_away_triggered = Column(Boolean, nullable=False, default=False)

    # Flexible Detail
    violations_detail = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    session = relationship("NegotiationSession", back_populates="analytics")
