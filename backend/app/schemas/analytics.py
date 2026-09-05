"""Additive analytics response contract. Missing market measurements stay null."""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel
from app.schemas.watchlist_changes import ReasonOut

class AnalyticsIdentity(BaseModel):
    symbol: str
    company_name: str
    exchange: str
    sector: str | None
    is_in_watchlist: bool

class AnalyticsFreshness(BaseModel):
    status: str
    observed_at: datetime | None
    source: str
    age_minutes: int | None
    market_status: str | None

class AnalyticsObservation(BaseModel):
    current_price: float | None
    observed_at: datetime | None
    source: str | None
    freshness: AnalyticsFreshness
    session_date: date | None

class AnalyticsTemporal(BaseModel):
    previous_session_close: float | None
    previous_session_date: date | None
    previous_session_observed_at: datetime | None
    session_change_pct: float | None
    session_return: float | None
    last_viewed_price: float | None
    last_viewed_at: datetime | None
    since_last_view_pct: float | None
    since_view_return: float | None
    five_session_return_pct: float | None = None
    twenty_session_return_pct: float | None = None

class AnalyticsVolume(BaseModel):
    current_session_volume: float | None
    baseline_average_volume: float | None
    baseline_sample_count: int
    volume_ratio: float | None

class AnalyticsVolatility(BaseModel):
    canonical_value: float
    raw_value: float | None
    effective_floor: float
    floor_applied: bool
    sample_count: int
    unusualness_ratio: float

class AnalyticsTechnical(BaseModel):
    previous_window_max_close: float
    sample_count: int
    is_new_high: bool
    high_20d: float | None = None
    low_20d: float | None = None
    distance_from_20d_high_pct: float | None = None

class AnalyticsAttention(BaseModel):
    return_contribution: float
    volume_contribution: float
    technical_contribution: float
    objective_exact: float
    objective_score: float

class AnalyticsPersonal(BaseModel):
    since_view_contribution: float
    profile_contribution: float
    profile_reasons: list[ReasonOut]
    personal_exact: float
    preference_fit: float

class AnalyticsFinal(BaseModel):
    attention_score: float
    attention_level: Literal['LOW','MEDIUM','HIGH']
    cap: float

class AnalyticsAvailability(BaseModel):
    analytics_available: bool
    reason: str | None
    available_history_count: int = 0


class AnalyticsHistoryPoint(BaseModel):
    timestamp: datetime
    close: float
    volume: int
    source: str

class AnalyticsOut(BaseModel):
    identity: AnalyticsIdentity
    observation: AnalyticsObservation
    temporal: AnalyticsTemporal
    volume: AnalyticsVolume
    volatility: AnalyticsVolatility | None
    technical: AnalyticsTechnical | None
    attention: AnalyticsAttention | None
    personal: AnalyticsPersonal | None
    final: AnalyticsFinal | None
    availability: AnalyticsAvailability
    reasons: list[ReasonOut]
    history: list[AnalyticsHistoryPoint]
