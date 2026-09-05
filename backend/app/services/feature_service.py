"""
Feature extraction from raw market observations.

CRITICAL: Extracts features using TRADING-SESSION boundaries, not poll intervals.
All calculations (session_return, volatility_20d, volume_ratio, 20d_high)
operate on distinct trading sessions, not the last N consecutive polls.

A trading session is defined as market hours on a calendar date:
- IST: 09:15 to 15:30
- Excludes weekends
"""

from datetime import datetime, date
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.repositories import stock_repository, view_state_repository
from app.services.attention_service import MarketFeatures

IST = ZoneInfo("Asia/Kolkata")


def get_session_date(timestamp: datetime) -> date:
    """
    Get the trading session date for a timestamp.
    
    Converts UTC → IST and extracts date.
    All observations on the same IST calendar date belong to the same session.
    """
    ist_time = timestamp.astimezone(IST)
    return ist_time.date()


def group_snapshots_by_session(snapshots: list) -> list[tuple]:
    """
    Group snapshots by trading session (IST date).
    
    Args:
        snapshots: List of PriceSnapshot sorted oldest → newest
        
    Returns:
        List of (session_date, [snapshots in that session])
    """
    if not snapshots:
        return []
    
    sessions = {}
    for snap in snapshots:
        session_date = get_session_date(snap.timestamp)
        if session_date not in sessions:
            sessions[session_date] = []
        sessions[session_date].append(snap)
    
    # Return sorted by date
    return [(date, sessions[date]) for date in sorted(sessions.keys())]


def get_session_close(session_snapshots: list) -> float:
    """Get the closing price for a session (last observation)."""
    return float(session_snapshots[-1].close)


def get_session_volume(session_snapshots: list) -> float:
    """
    Volume for a session, taken from the latest observation in that session.
    For historical single-snapshot sessions, this is that day's total volume.
    For an in-progress live session, this represents cumulative volume so far --
    not the sum of independently-sampled per-poll volumes, which double-counts.
    """
    return float(session_snapshots[-1].volume)


def calculate_daily_returns_from_sessions(session_closes: list[float]) -> list[float]:
    """
    Calculate daily returns from session closes.
    
    Args:
        session_closes: List of session close prices in chronological order
        
    Returns:
        List of daily returns: r_t = (close_t / close_t_minus_1) - 1
    """
    if len(session_closes) < 2:
        return []
    
    returns = []
    for i in range(1, len(session_closes)):
        ret = (session_closes[i] / session_closes[i-1]) - 1
        returns.append(ret)
    return returns


def calculate_volatility_20d_from_sessions(session_closes: list[float]) -> float:
    """
    Calculate 20-day rolling volatility from session closes.
    
    Args:
        session_closes: List of session close prices (in chronological order)
        
    Returns:
        Standard deviation of daily returns
    """
    returns = calculate_daily_returns_from_sessions(session_closes)
    
    if not returns:
        return 0.005  # Safe default
    
    # Use last 20 returns
    recent_returns = returns[-20:] if len(returns) >= 20 else returns
    
    if len(recent_returns) < 2:
        return 0.005
    
    mean_ret = sum(recent_returns) / len(recent_returns)
    variance = sum((r - mean_ret) ** 2 for r in recent_returns) / len(recent_returns)
    volatility = variance ** 0.5
    
    return max(volatility, 0.005)  # Floor at 0.5%


def extract_features(
    db: Session,
    stock_id: str,
    user_id: str,
) -> MarketFeatures | None:
    """
    Extract MarketFeatures for a stock using TRADING-SESSION boundaries.
    
    Args:
        db: Database session
        stock_id: Stock ID
        user_id: User ID for viewing baseline
        
    Returns:
        MarketFeatures or None if insufficient data
    """
    # Get all snapshots sorted oldest first
    snapshots = stock_repository.get_history(db, stock_id)
    
    if len(snapshots) < 2:
        return None  # Need at least 2 observations to compare
    
    # Group by trading session
    sessions = group_snapshots_by_session(snapshots)
    
    if len(sessions) < 2:
        # Need at least 2 sessions (previous + current)
        return None
    
    # Get session closes and volumes
    session_closes = [get_session_close(snaps) for _, snaps in sessions]
    session_volumes = [get_session_volume(snaps) for _, snaps in sessions]
    
    # Current session is the last one
    latest_session_close = session_closes[-1]
    previous_session_close = session_closes[-2]
    
    # Session return: current session close vs previous session close
    session_return = (latest_session_close / previous_session_close) - 1
    
    # Volatility from last 20 daily returns (20+ sessions needed)
    volatility_20d = calculate_volatility_20d_from_sessions(session_closes)
    
    # Volume ratio: current session volume / average of previous 20 sessions
    recent_volumes = session_volumes[-21:-1]  # Exclude current session
    if recent_volumes:
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        volume_ratio = session_volumes[-1] / avg_volume if avg_volume > 0 else 1.0
    else:
        volume_ratio = 1.0
    
    # Since-view return: current close vs last viewed price
    view_state = view_state_repository.get_for_user_stock(db, user_id, stock_id)
    since_view_return = None
    if view_state:
        since_view_return = (latest_session_close / float(view_state.last_viewed_price)) - 1
    
    # New 20-day high: current > max(previous 20 session closes)
    historical_closes = session_closes[-21:-1]  # Previous 20, exclude current
    if historical_closes:
        max_20d = max(historical_closes)
        new_20d_high = latest_session_close > max_20d
    else:
        new_20d_high = False
    
    return MarketFeatures(
        session_return=session_return,
        volatility_20d=volatility_20d,
        volume_ratio=volume_ratio,
        since_view_return=since_view_return,
        new_20d_high=new_20d_high,
    )
