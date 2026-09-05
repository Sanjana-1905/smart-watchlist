"""Read-only projection of the canonical engine; no independent scoring rules."""
from dataclasses import asdict
from app.core.errors import AppError
from app.core.freshness import evaluate_freshness
from app.repositories import stock_repository, view_state_repository, profile_repository, watchlist_repository
from app.services.feature_service import (extract_features, group_snapshots_by_session, get_session_close,
    get_session_volume, calculate_daily_returns_from_sessions)
from app.services.attention_service import (UserPreferences, calculate_attention, calculate_unusual_return_points,
    calculate_volume_points, calculate_technical_points, calculate_since_view_points, calculate_preference_fit)


def build_analytics(db, stock, user_id):
    profile = profile_repository.get_for_user(db, user_id)
    if not profile:
        raise AppError(404, "PROFILE_NOT_FOUND", "No profile found for user")
    history = stock_repository.get_history(db, stock.id)
    sessions = group_snapshots_by_session(history)
    closes = [get_session_close(rows) for _, rows in sessions]
    volumes = [get_session_volume(rows) for _, rows in sessions]
    view = view_state_repository.get_for_user_stock(db, user_id, stock.id)
    latest = history[-1] if history else None
    features = extract_features(db, stock.id, user_id)
    freshness = evaluate_freshness(latest.timestamp if latest else None, latest.source if latest else 'unknown')
    five_ret = round(((closes[-1] / closes[-6]) - 1) * 100, 2) if len(closes) >= 6 else None
    twenty_ret = round(((closes[-1] / closes[-21]) - 1) * 100, 2) if len(closes) >= 21 else None
    recent_20 = closes[-20:] if len(closes) >= 20 else closes
    high_20d = max(recent_20) if recent_20 else None
    low_20d = min(recent_20) if recent_20 else None
    dist_high = round(((closes[-1] / high_20d) - 1) * 100, 2) if high_20d and high_20d > 0 else None

    response = {
        'identity': dict(symbol=stock.symbol, company_name=stock.company_name, exchange=stock.exchange,
            sector=stock.sector, is_in_watchlist=watchlist_repository.get_item(db, user_id, stock.id) is not None),
        'observation': dict(current_price=float(latest.close) if latest else None,
            observed_at=latest.timestamp if latest else None, source=latest.source if latest else None,
            freshness=asdict(freshness), session_date=sessions[-1][0] if sessions else None),
        'temporal': dict(previous_session_close=closes[-2] if len(closes) >= 2 else None,
            previous_session_date=sessions[-2][0] if len(sessions) >= 2 else None,
            previous_session_observed_at=sessions[-2][1][-1].timestamp if len(sessions) >= 2 else None,
            session_change_pct=features.session_return * 100 if features else None,
            session_return=features.session_return if features else None,
            last_viewed_price=float(view.last_viewed_price) if view else None,
            last_viewed_at=view.last_viewed_at if view else None,
            since_last_view_pct=features.since_view_return * 100 if features and features.since_view_return is not None else None,
            since_view_return=features.since_view_return if features else None,
            five_session_return_pct=five_ret,
            twenty_session_return_pct=twenty_ret),
        'volume': dict(current_session_volume=volumes[-1] if volumes else None,
            baseline_average_volume=sum(volumes[-21:-1])/len(volumes[-21:-1]) if len(volumes)>1 else None,
            baseline_sample_count=len(volumes[-21:-1]), volume_ratio=features.volume_ratio if features else None),
        'volatility': None, 'technical': None, 'attention': None, 'personal': None, 'final': None,
        'reasons': [],
        'availability': dict(analytics_available=features is not None,
            reason=None if features else f'{len(sessions)} session(s) available; 2 distinct trading sessions required.',
            available_history_count=len(history)),
        'history': [dict(timestamp=row.timestamp, close=float(row.close), volume=row.volume, source=row.source) for row in history],
    }
    if not features:
        return response
    preferences = UserPreferences(profile.risk_profile, profile.attention_style, profile.time_horizon)
    result = calculate_attention(features, preferences)
    returns = calculate_daily_returns_from_sessions(closes)[-20:]
    raw_volatility = (sum((r - sum(returns)/len(returns))**2 for r in returns)/len(returns))**0.5 if len(returns)>=2 else None
    return_pts, _ = calculate_unusual_return_points(features.session_return, features.volatility_20d)
    volume_pts, _ = calculate_volume_points(features.volume_ratio)
    technical_pts, _ = calculate_technical_points(features.new_20d_high)
    view_pts, _ = calculate_since_view_points(features.since_view_return)
    profile_pts, profile_reasons = calculate_preference_fit(features, preferences)
    response.update(
        volatility=dict(canonical_value=features.volatility_20d, raw_value=raw_volatility, effective_floor=0.005,
            floor_applied=raw_volatility is None or raw_volatility<0.005, sample_count=len(returns),
            unusualness_ratio=abs(features.session_return)/features.volatility_20d),
        technical=dict(previous_window_max_close=max(closes[-21:-1]), sample_count=len(closes[-21:-1]), is_new_high=features.new_20d_high,
            high_20d=high_20d, low_20d=low_20d, distance_from_20d_high_pct=dist_high),
        attention=dict(return_contribution=return_pts, volume_contribution=volume_pts, technical_contribution=technical_pts,
            objective_exact=return_pts+volume_pts+technical_pts, objective_score=result.objective_score),
        personal=dict(since_view_contribution=view_pts, profile_contribution=profile_pts,
            profile_reasons=[asdict(reason) for reason in profile_reasons], personal_exact=view_pts+profile_pts, preference_fit=result.preference_fit),
        final=dict(attention_score=result.final_score, attention_level=result.level, cap=100),
        reasons=[asdict(reason) for reason in result.reasons],
    )
    return response
