import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, NUMERIC, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from ..database.base import Base


class MarketPriceSnapshot(Base):
    __tablename__ = "market_price_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    product_id = Column(String(100), nullable=False, index=True)

    market_avg_price = Column(NUMERIC(19, 4), nullable=False)
    lowest_price = Column(NUMERIC(19, 4), nullable=False)
    highest_price = Column(NUMERIC(19, 4), nullable=False)

    competitor_count = Column(Integer, nullable=True)
    competition_density = Column(NUMERIC(7, 4), nullable=True)

    collected_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_market_product_collected", "product_id", "collected_at"),
    )
