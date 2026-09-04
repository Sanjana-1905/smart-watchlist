import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Stock(Base):
    __tablename__ = "stocks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String, unique=True, nullable=False, index=True)
    company_name = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    sector = Column(String, nullable=True)