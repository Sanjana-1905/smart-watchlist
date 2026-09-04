import uuid
from sqlalchemy import Column, DateTime, Numeric, BigInteger, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_id = Column(UUID(as_uuid=True), ForeignKey("stocks.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    open = Column(Numeric, nullable=False)
    high = Column(Numeric, nullable=False)
    low = Column(Numeric, nullable=False)
    close = Column(Numeric, nullable=False)
    volume = Column(BigInteger, nullable=False)
    source = Column(String, nullable=False)

    __table_args__ = (Index("idx_price_stock_time", "stock_id", "timestamp"),)