"""
Feature extraction from raw market observations.

Converts PostgreSQL snapshots into normalized features suitable for
attention scoring. Handles all database and calculation complexity.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories import stock_repository, view_state_repository
from app.services.attention_service import MarketFeatures


def calculate_daily_returns(closes: list[float]) -> list[float]:
    """
    Calculate daily returns from a sequence of closes.
    
    Args:
        closes: List of closes in chronological order
        
    Returns:
        List of returns: r_t = (close_t / close_t_minus_1) - 1
    """
    if len(closes) < 2:
        return []
    
    returns = []
    for i in range(1, len(closes)):
        ret = (closes[i] / closes[i-1]) - 1
        returns.append(ret)
    return returns


def calculate_volatility_20d(closes: list[float]) -> float:
    """
    Calculate 20-day rolling volatility as std dev of daily returns.
    
    Args:
        closes: List of closes in chronological order
        
    Returns:
        Standard deviation of daily returns (e.g., 0.025 for 2.5%)
    """
    returns = calculate_daily_returns(closes)
    
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
    Extract MarketFeatures for a stock given the user's viewing state.
    
    This function:
    1. Retrieves the last 21 snapshots (20 historical + current)
    2. Calculates session_return from current vs previous close
    3. Calculates volatility_20d from daily returns
    4. Calculates volume_ratio from current vs 20-day average
    5. Retrieves user's last viewed price and calculates since_view_return
    6. Checks if current is a new 20-day high
    
    Args:
        db: Database session
        stock_id: Stock ID
        user_id: User ID
        
    Returns:
        MarketFeatures or None if insufficient data
    """
    # Get last 21 snapshots (20 for calculation + 1 current)
    snapshots = stock_repository.get_history(db, stock_id)
    
    if len(snapshots) < 2:
        return None  # Need at least previous close + current
    
    # Most recent snapshots are sorted oldest first
    snapshots = sorted(snapshots, key=lambda s: s.timestamp)
    latest_snap = snapshots[-1]
    previous_snap = snapshots[-2]
    
    # Session return: current vs previous close
    session_return = (latest_snap.close / previous_snap.close) - 1
    
    # Volatility from daily returns
    closes = [float(s.close) for s in snapshots[-21:]]  # Last 21
    volatility_20d = calculate_volatility_20d(closes)
    
    # Volume ratio: current volume / 20-day average
    volumes = [float(s.volume) for s in snapshots[-20:]]  # Last 20
    avg_volume = sum(volumes) / len(volumes) if volumes else 1
    volume_ratio = float(latest_snap.volume) / avg_volume if avg_volume > 0 else 1.0
    
    # Since-view return: current vs last viewed price
    view_state = view_state_repository.get_for_user_stock(db, user_id, stock_id)
    since_view_return = None
    if view_state:
        since_view_return = (
            float(latest_snap.close) / float(view_state.last_viewed_price)
        ) - 1
    
    # New 20-day high: current > max(previous 20)
    historical_closes = [float(s.close) for s in snapshots[-21:-1]]  # Exclude current
    max_20d = max(historical_closes) if historical_closes else 0
    new_20d_high = float(latest_snap.close) > max_20d
    
    return MarketFeatures(
        session_return=session_return,
        volatility_20d=volatility_20d,
        volume_ratio=volume_ratio,
        since_view_return=since_view_return,
        new_20d_high=new_20d_high,
    )
