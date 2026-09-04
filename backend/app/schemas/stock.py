from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class StockOut(BaseModel):
    id: UUID
    symbol: str
    company_name: str
    exchange: str
    sector: str | None

    class Config:
        from_attributes = True

class PriceSnapshotOut(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    source: str

    class Config:
        from_attributes = True