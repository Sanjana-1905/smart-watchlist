from datetime import datetime, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

class MarketStatus:
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRE_OPEN = "PRE_OPEN"

def get_market_status(now: datetime | None = None) -> str:
    """
    NSE market hours: 09:15 - 15:30 IST, Monday-Friday.
    
    Args:
        now: Optional datetime to evaluate. Defaults to current UTC time.
        
    Returns:
        MarketStatus.OPEN, CLOSED, or PRE_OPEN
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    now_ist = now.astimezone(IST)
    
    # Check if it's a weekend (Saturday=5, Sunday=6)
    if now_ist.weekday() >= 5:
        return MarketStatus.CLOSED
    
    hour, minute = now_ist.hour, now_ist.minute
    time_minutes = hour * 60 + minute
    
    open_minutes = 9 * 60 + 15      # 09:15
    close_minutes = 15 * 60 + 30    # 15:30
    
    if time_minutes < open_minutes:
        return MarketStatus.PRE_OPEN
    elif time_minutes <= close_minutes:
        return MarketStatus.OPEN
    else:
        return MarketStatus.CLOSED

def is_market_open(now: datetime | None = None) -> bool:
    """Check if market is currently open."""
    return get_market_status(now) == MarketStatus.OPEN
