from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from app.core.market_clock import get_market_status, MarketStatus

class FreshnessStatus:
    FRESH = "FRESH"
    DELAYED = "DELAYED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"

@dataclass
class FreshnessInfo:
    """
    Market observation freshness, independent of market status.
    
    FRESH:       ≤2 minutes old
    DELAYED:     >2 and ≤10 minutes old
    STALE:       >10 minutes old
    UNAVAILABLE: no observation exists
    """
    status: str
    observed_at: datetime | None
    source: str
    age_minutes: int | None = None
    market_status: str | None = None

def evaluate_freshness(
    last_observation_timestamp: datetime | None,
    source: str,
    now: datetime | None = None,
) -> FreshnessInfo:
    """
    Evaluate data freshness independently of market status.
    
    Freshness is about data age:
    - FRESH: ≤2 min
    - DELAYED: >2, ≤10 min
    - STALE: >10 min
    - UNAVAILABLE: no data
    
    Market status is separate — returned independently so UI can
    render "Market closed · Last observation: Friday 3:30 PM"
    without confusing data quality with market hours.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    market_status = get_market_status(now)
    
    if last_observation_timestamp is None:
        return FreshnessInfo(
            status=FreshnessStatus.UNAVAILABLE,
            observed_at=None,
            source=source,
            market_status=market_status,
        )
    
    age = now - last_observation_timestamp
    age_minutes = int(age.total_seconds() / 60)
    
    # Freshness is determined by age alone
    if age <= timedelta(minutes=2):
        status = FreshnessStatus.FRESH
    elif age <= timedelta(minutes=10):
        status = FreshnessStatus.DELAYED
    else:
        status = FreshnessStatus.STALE
    
    return FreshnessInfo(
        status=status,
        observed_at=last_observation_timestamp,
        source=source,
        age_minutes=age_minutes,
        market_status=market_status,
    )
