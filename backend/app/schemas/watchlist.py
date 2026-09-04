from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class WatchlistItemOut(BaseModel):
    symbol: str
    company_name: str
    added_at: datetime

class AddWatchlistItemIn(BaseModel):
    symbol: str

class ViewedIn(BaseModel):
    symbol: str