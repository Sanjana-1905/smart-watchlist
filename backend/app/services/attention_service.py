"""
Pure attention scoring engine.

No FastAPI, no SQLAlchemy, no HTTP — just math and logic.
This is the core IP of the product.

Objective score: 0-100, based on market facts alone.
Preference fit: 0-15, based on user preferences.
Final score: min(objective + preference_fit, 100).
"""

from dataclasses import dataclass


@dataclass
class MarketFeatures:
    """Raw market observations for a stock."""
    session_return: float           # e.g., 0.048 for +4.8%
    volatility_20d: float           # e.g., 0.025 for 2.5% daily std dev
    volume_ratio: float             # e.g., 1.6 for 60% above normal
    since_view_return: float | None # e.g., 0.043 for +4.3%, or None if never viewed
    new_20d_high: bool              # True if current > max(last 20 closes)


@dataclass
class UserPreferences:
    """User's attention preferences."""
    risk_profile: str       # CONSERVATIVE, BALANCED, AGGRESSIVE
    attention_style: str    # MOMENTUM, STABILITY, BALANCED
    time_horizon: str       # SHORT_TERM, LONG_TERM


@dataclass
class AttentionReason:
    """Single reason for attention ranking."""
    type: str               # UNUSUAL_RETURN, VOLUME, SINCE_VIEW, NEW_HIGH, PREFERENCE
    value: float | str | bool
    message: str


@dataclass
class AttentionResult:
    """Final attention score and breakdown."""
    objective_score: float
    preference_fit: float
    final_score: float
    level: str              # LOW, MEDIUM, HIGH
    reasons: list[AttentionReason]


# ============================================================================
# OBJECTIVE SCORING
# ============================================================================

def calculate_unusual_return_points(
    session_return: float,
    volatility_20d: float,
) -> tuple[float, AttentionReason | None]:
    """
    Unusual movement: 45 points max
    
    unusual_return = abs(session_return) / volatility_20d
    
    1σ  → 15 points
    2σ  → 30 points
    3σ+ → 45 points
    
    Returns reason only if unusualness >= 1.0σ (meaningful signal).
    """
    volatility = max(volatility_20d, 0.005)
    unusual_return = abs(session_return) / volatility
    points = min(unusual_return / 3.0, 1.0) * 45
    
    # Only emit reason if meaningfully unusual (>= 1σ)
    if unusual_return < 1.0:
        return points, None
    
    reason = AttentionReason(
        type="UNUSUAL_RETURN",
        value=round(unusual_return, 2),
        message=f"Price move is {unusual_return:.1f}× normal daily volatility",
    )
    return points, reason


def calculate_volume_points(volume_ratio: float) -> tuple[float, AttentionReason | None]:
    """
    Volume anomaly: 25 points max
    
    Use only the abnormal part above 1.0×
    cap at 1.5× excess volume = 25 points
    
    1.0× volume → 0 points, no reason
    1.5× volume → 8 points
    2.0× volume → 17 points
    2.5×+ volume → 25 points
    
    Returns reason only if volume >= 1.3× (notable).
    """
    volume_anomaly = max(volume_ratio - 1.0, 0)
    points = min(volume_anomaly / 1.5, 1.0) * 25
    
    # Only emit reason if notably elevated (>= 1.3×)
    if volume_ratio < 1.3:
        return points, None
    
    reason = AttentionReason(
        type="VOLUME",
        value=round(volume_ratio, 2),
        message=f"Volume is {volume_ratio:.1f}× its 20-day average",
    )
    return points, reason


def calculate_since_view_points(
    since_view_return: float | None,
) -> tuple[float, AttentionReason | None]:
    """
    Change since last viewed: 20 points max
    
    Cap at 5% move
    
    0% → 0 points
    1% → 4 points
    2.5% → 10 points
    5%+ → 20 points
    
    Returns reason only if |return| >= 1% (meaningful change).
    """
    if since_view_return is None:
        return 0.0, None
    
    abs_return = abs(since_view_return)
    points = min(abs_return / 0.05, 1.0) * 20
    
    # Only emit reason if meaningfully changed (>= 1%)
    if abs_return < 0.01:
        return points, None
    
    direction = "+" if since_view_return > 0 else ""
    reason = AttentionReason(
        type="SINCE_VIEW",
        value=round(since_view_return * 100, 1),
        message=f"{direction}{since_view_return*100:.1f}% since you last checked",
    )
    return points, reason


def calculate_technical_points(new_20d_high: bool) -> tuple[float, AttentionReason | None]:
    """
    New 20-day high: 10 points if true, 0 if false.
    
    Always emit reason if true (technical context matters).
    """
    points = 10.0 if new_20d_high else 0.0
    
    if not new_20d_high:
        return points, None
    
    reason = AttentionReason(
        type="NEW_HIGH",
        value=True,
        message="Reached a new 20-day high",
    )
    return points, reason


def calculate_objective_score(features: MarketFeatures) -> tuple[float, list[AttentionReason]]:
    """
    Calculate objective attention score (0-100) from market facts.
    
    Same market facts → same score, always.
    Independent of user preferences.
    """
    unusual_pts, unusual_reason = calculate_unusual_return_points(
        features.session_return,
        features.volatility_20d,
    )
    volume_pts, volume_reason = calculate_volume_points(features.volume_ratio)
    view_pts, view_reason = calculate_since_view_points(features.since_view_return)
    tech_pts, tech_reason = calculate_technical_points(features.new_20d_high)
    
    objective_score = min(
        unusual_pts + volume_pts + view_pts + tech_pts,
        100.0,
    )
    
    # Collect only meaningful reasons
    reasons = []
    if unusual_reason:
        reasons.append(unusual_reason)
    if volume_reason:
        reasons.append(volume_reason)
    if view_reason:
        reasons.append(view_reason)
    if tech_reason:
        reasons.append(tech_reason)
    
    return objective_score, reasons


# ============================================================================
# PREFERENCE FIT
# ============================================================================

def calculate_preference_fit(
    features: MarketFeatures,
    preferences: UserPreferences,
) -> tuple[float, list[AttentionReason]]:
    """
    Calculate preference bonus (0-15) based on user's attention style.
    
    Each dimension can contribute +0 or +5:
    - attention_style
    - risk_profile
    - time_horizon
    
    Max: +15 total (added to objective, capped at 100 final).
    
    Important: We're not recommending what to buy.
    We're ranking what deserves the user's *attention first*.
    """
    fit = 0.0
    reasons = []
    
    volatility = max(features.volatility_20d, 0.005)
    unusual_return = abs(features.session_return) / volatility
    
    # Attention style bonus
    if preferences.attention_style == "MOMENTUM":
        if features.session_return > 0 and unusual_return >= 1.5:
            fit += 5.0
            reasons.append(AttentionReason(
                type="PREFERENCE",
                value="MOMENTUM",
                message="Positive momentum aligns with your attention preference",
            ))
    elif preferences.attention_style == "STABILITY":
        if features.session_return < 0 and unusual_return >= 1.5:
            fit += 5.0
            reasons.append(AttentionReason(
                type="PREFERENCE",
                value="STABILITY",
                message="Unusual downside movement deserves attention in your profile",
            ))
    
    # Risk profile bonus
    if preferences.risk_profile == "AGGRESSIVE":
        if features.session_return > 0 and unusual_return >= 1.5:
            fit += 5.0
            reasons.append(AttentionReason(
                type="PREFERENCE",
                value="AGGRESSIVE",
                message="Upside volatility aligns with your risk profile",
            ))
    elif preferences.risk_profile == "CONSERVATIVE":
        if features.session_return < 0 and unusual_return >= 1.5:
            fit += 5.0
            reasons.append(AttentionReason(
                type="PREFERENCE",
                value="CONSERVATIVE",
                message="Downside risk warrants closer monitoring per your profile",
            ))
    
    # Time horizon bonus
    if preferences.time_horizon == "SHORT_TERM":
        if features.since_view_return is not None and abs(features.since_view_return) >= 0.02:
            fit += 5.0
            reasons.append(AttentionReason(
                type="PREFERENCE",
                value="SHORT_TERM",
                message="Recent movement is especially relevant to your short-term focus",
            ))
    
    return fit, reasons


# ============================================================================
# FINAL SCORING
# ============================================================================

def classify_level(score: float) -> str:
    """Classify attention score into bands."""
    if score >= 80:
        return "HIGH"
    elif score >= 50:
        return "MEDIUM"
    else:
        return "LOW"


def calculate_attention(
    features: MarketFeatures,
    preferences: UserPreferences,
) -> AttentionResult:
    """
    Calculate complete attention score and reasons.
    
    Args:
        features: Raw market observations (from feature_service)
        preferences: User's attention preferences (from database)
        
    Returns:
        AttentionResult with objective score, preference fit, final score, level, and reasons
    """
    objective_score, objective_reasons = calculate_objective_score(features)
    preference_fit, preference_reasons = calculate_preference_fit(features, preferences)
    
    final_score = min(objective_score + preference_fit, 100.0)
    level = classify_level(final_score)
    
    all_reasons = objective_reasons + preference_reasons
    
    return AttentionResult(
        objective_score=round(objective_score, 1),
        preference_fit=round(preference_fit, 1),
        final_score=round(final_score, 1),
        level=level,
        reasons=all_reasons,
    )
