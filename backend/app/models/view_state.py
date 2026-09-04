from sqlalchemy import Column, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class UserViewState(Base):
    __tablename__ = "user_view_state"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    stock_id = Column(UUID(as_uuid=True), ForeignKey("stocks.id"), primary_key=True)
    last_viewed_at = Column(DateTime(timezone=True), nullable=False)
    last_viewed_price = Column(Numeric, nullable=False)