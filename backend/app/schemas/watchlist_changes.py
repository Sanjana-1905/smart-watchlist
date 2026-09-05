from pydantic import BaseModel, Field
from datetime import datetime


class ReasonOut(BaseModel):
    """Single reason for attention ranking."""
    type: str
    value: float | str | bool
    message: str


class FreshnessOut(BaseModel):
    """Market data freshness metadata."""
    status: str
    observed_at: datetime
    source: str
    age_minutes: int | None = None


class WatchlistChangeItemOut(BaseModel):
    """Single item in the attention-ranked watchlist."""
    symbol: str
    company_name: str
    current_price: float
    session_change_pct: float
    since_last_view_pct: float | None
    
    objective_score: float
    preference_fit: float = Field(description="Personal relevance: since-view movement (0-20) plus profile bonus (0-15)")
    attention_score: float
    attention_level: str
    
    reasons: list[ReasonOut]
    freshness: FreshnessOut


class WatchlistChangesOut(BaseModel):
    """Complete attention-ranked watchlist response."""
    generated_at: datetime
    market_status: str
    items: list[WatchlistChangeItemOut]
