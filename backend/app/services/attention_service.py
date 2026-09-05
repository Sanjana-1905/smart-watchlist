"""
Pure attention scoring engine.

No FastAPI, SQLAlchemy, HTTP, or database access lives here.
The module receives already-extracted market features and user preferences
and returns a deterministic, explainable Attention Score.

Scoring model
-------------
Market Significance (objective, user-independent):
    unusual price movement     0-45
    relative volume            0-25
    technical context          0-10
                               ----
    maximum                    0-80

Personal Relevance (user-dependent):
    since-last-view movement   0-20
    profile relevance          0-15
                               ----
    maximum                    0-35

Final Attention Score:
    min(Market Significance + Personal Relevance, 100)

Important invariant:
The same market observations produce the same objective score for every user.
Only Personal Relevance can vary by user.

The legacy response field `preference_fit` carries the combined Personal
Relevance value (since-view contribution + profile contribution).
"""

from dataclasses import dataclass


# ============================================================================
# DOMAIN TYPES
# ============================================================================


@dataclass
class MarketFeatures:
    """Market observations required by the attention engine."""

    # Current trading-session return as a decimal.
    # Example: 0.048 means +4.8%.
    session_return: float

    # Recent daily/session return volatility as a decimal.
    # Example: 0.025 means 2.5%.
    volatility_20d: float

    # Current session volume / recent average volume.
    # Example: 1.6 means 60% above normal.
    volume_ratio: float

    # Current price relative to this user's last acknowledged price.
    # None means that the user does not yet have a baseline.
    since_view_return: float | None

    # Whether the current close exceeded the preceding 20-session maximum.
    new_20d_high: bool


@dataclass
class UserPreferences:
    """Explicit attention preferences belonging to one user."""

    # CONSERVATIVE | BALANCED | AGGRESSIVE
    risk_profile: str

    # MOMENTUM | STABILITY | BALANCED
    attention_style: str

    # SHORT_TERM | LONG_TERM
    time_horizon: str


@dataclass
class AttentionReason:
    """One human-readable reason contributing to attention."""

    # Typical values:
    # UNUSUAL_RETURN, VOLUME, SINCE_VIEW, NEW_HIGH, PREFERENCE
    type: str

    value: float | str | bool
    message: str


@dataclass
class AttentionResult:
    """Final score and its explainable decomposition."""

    # Objective Market Significance, normally 0-80.
    objective_score: float

    # Legacy API field containing total Personal Relevance:
    # since-view contribution (0-20) + profile contribution (0-15).
    preference_fit: float

    # min(objective_score + preference_fit, 100)
    final_score: float

    # LOW | MEDIUM | HIGH
    level: str

    reasons: list[AttentionReason]


# ============================================================================
# OBJECTIVE MARKET SIGNIFICANCE
# ============================================================================


def calculate_unusual_return_points(
    session_return: float,
    volatility_20d: float,
) -> tuple[float, AttentionReason | None]:
    """
    Score how unusual the current price movement is.

    Maximum: 45 points.

    unusualness =
        abs(session_return) / max(volatility_20d, 0.5%)

    Approximate scale:
        0σ -> 0
        1σ -> 15
        2σ -> 30
        3σ+ -> 45

    The score is continuous, while an explanation reason is emitted only
    once the movement reaches 1σ.
    """

    volatility = max(float(volatility_20d), 0.005)

    unusual_return = abs(float(session_return)) / volatility

    points = min(
        unusual_return / 3.0,
        1.0,
    ) * 45.0

    if unusual_return < 1.0:
        return points, None

    reason = AttentionReason(
        type="UNUSUAL_RETURN",
        value=round(unusual_return, 2),
        message=(
            f"Price move is {unusual_return:.1f}× "
            "normal daily volatility"
        ),
    )

    return points, reason


def calculate_volume_points(
    volume_ratio: float,
) -> tuple[float, AttentionReason | None]:
    """
    Score abnormal trading volume.

    Maximum: 25 points.

    Only volume above the normal 1.0× baseline contributes.

        1.0× -> 0
        1.5× -> ~8
        2.0× -> ~17
        2.5×+ -> 25

    An explanation reason is emitted from 1.3× upward.
    """

    ratio = max(float(volume_ratio), 0.0)

    volume_anomaly = max(
        ratio - 1.0,
        0.0,
    )

    points = min(
        volume_anomaly / 1.5,
        1.0,
    ) * 25.0

    if ratio < 1.3:
        return points, None

    reason = AttentionReason(
        type="VOLUME",
        value=round(ratio, 2),
        message=f"Volume is {ratio:.1f}× its 20-day average",
    )

    return points, reason


def calculate_technical_points(
    new_20d_high: bool,
) -> tuple[float, AttentionReason | None]:
    """
    Add technical context for a new 20-session high.

    Maximum: 10 points.
    """

    if not new_20d_high:
        return 0.0, None

    reason = AttentionReason(
        type="NEW_HIGH",
        value=True,
        message="Reached a new 20-day high",
    )

    return 10.0, reason


def calculate_objective_score(
    features: MarketFeatures,
) -> tuple[float, list[AttentionReason]]:
    """
    Calculate Market Significance from market facts only.

    This function MUST NOT use:
    - user profile
    - risk preference
    - attention style
    - time horizon
    - user's last-view movement

    Maximum raw objective score: 80.

    This is the key architecture invariant:

        same market facts
            ->
        same objective score
            ->
        regardless of user
    """

    unusual_points, unusual_reason = calculate_unusual_return_points(
        features.session_return,
        features.volatility_20d,
    )

    volume_points, volume_reason = calculate_volume_points(
        features.volume_ratio
    )

    technical_points, technical_reason = calculate_technical_points(
        features.new_20d_high
    )

    objective_score = min(
        unusual_points
        + volume_points
        + technical_points,
        80.0,
    )

    reasons: list[AttentionReason] = []

    if unusual_reason is not None:
        reasons.append(unusual_reason)

    if volume_reason is not None:
        reasons.append(volume_reason)

    if technical_reason is not None:
        reasons.append(technical_reason)

    return objective_score, reasons


# ============================================================================
# SINCE-LAST-VIEW RELEVANCE
# ============================================================================


def calculate_since_view_points(
    since_view_return: float | None,
) -> tuple[float, AttentionReason | None]:
    """
    Score how much has changed since this user last acknowledged the stock.

    Maximum: 20 points.

        0%   -> 0
        1%   -> 4
        2.5% -> 10
        5%+  -> 20

    The score remains continuous below 1%, but a user-facing reason is only
    emitted from a 1% absolute change onward.

    None means there is no user baseline yet.
    """

    if since_view_return is None:
        return 0.0, None

    value = float(since_view_return)
    magnitude = abs(value)

    points = min(
        magnitude / 0.05,
        1.0,
    ) * 20.0

    if magnitude < 0.01:
        return points, None

    direction = "+" if value > 0 else ""

    reason = AttentionReason(
        type="SINCE_VIEW",
        value=round(value * 100.0, 1),
        message=(
            f"{direction}{value * 100.0:.1f}% "
            "since you last checked"
        ),
    )

    return points, reason


# ============================================================================
# PROFILE RELEVANCE
# ============================================================================


def calculate_preference_fit(
    features: MarketFeatures,
    preferences: UserPreferences,
) -> tuple[float, list[AttentionReason]]:
    """
    Calculate profile-specific relevance.

    Maximum: 15 points.

    There are three profile dimensions, each contributing at most 5:

        attention style   0-5
        risk profile      0-5
        time horizon      0-5

    Why continuous rather than binary thresholds?
    ----------------------------------------------
    The previous implementation awarded an entire +5 only after a market
    signal crossed a hard 1.5σ threshold. That created an arbitrary cliff:

        1.49σ -> 0 profile points
        1.50σ -> 5 profile points

    More importantly, ordinary but real market sessions could give both
    contrasting demo personas exactly zero profile contribution, making
    personalization invisible even though their profiles were correctly
    persisted and loaded.

    This implementation scales relevance continuously with the strength of
    the SAME objective market observations.

    It does not alter market facts or objective significance.
    """

    fit = 0.0
    reasons: list[AttentionReason] = []

    session_return = float(features.session_return)

    volatility = max(
        float(features.volatility_20d),
        0.005,
    )

    unusual_return = abs(session_return) / volatility

    # 0σ -> 0 relevance
    # 1.5σ+ -> full directional relevance
    movement_strength = min(
        unusual_return / 1.5,
        1.0,
    )

    # ------------------------------------------------------------------
    # 1. ATTENTION STYLE
    # ------------------------------------------------------------------

    if preferences.attention_style == "MOMENTUM":
        if session_return > 0:
            points = 5.0 * movement_strength
            fit += points

            if points > 0:
                reasons.append(
                    AttentionReason(
                        type="PREFERENCE",
                        value="MOMENTUM",
                        message=(
                            "Positive movement is relevant to your "
                            "momentum-focused attention style"
                        ),
                    )
                )

    elif preferences.attention_style == "STABILITY":
        if session_return < 0:
            points = 5.0 * movement_strength
            fit += points

            if points > 0:
                reasons.append(
                    AttentionReason(
                        type="PREFERENCE",
                        value="STABILITY",
                        message=(
                            "Downside movement is relevant to your "
                            "stability-focused attention style"
                        ),
                    )
                )

    # BALANCED intentionally receives no directional style bonus.

    # ------------------------------------------------------------------
    # 2. RISK PROFILE
    # ------------------------------------------------------------------

    if preferences.risk_profile == "AGGRESSIVE":
        if session_return > 0:
            points = 5.0 * movement_strength
            fit += points

            if points > 0:
                reasons.append(
                    AttentionReason(
                        type="PREFERENCE",
                        value="AGGRESSIVE",
                        message=(
                            "Upside volatility receives greater relevance "
                            "under your aggressive risk profile"
                        ),
                    )
                )

    elif preferences.risk_profile == "CONSERVATIVE":
        if session_return < 0:
            points = 5.0 * movement_strength
            fit += points

            if points > 0:
                reasons.append(
                    AttentionReason(
                        type="PREFERENCE",
                        value="CONSERVATIVE",
                        message=(
                            "Downside risk receives greater relevance "
                            "under your conservative risk profile"
                        ),
                    )
                )

    # BALANCED intentionally receives no directional risk bonus.

    # ------------------------------------------------------------------
    # 3. TIME HORIZON
    # ------------------------------------------------------------------

    if features.since_view_return is not None:
        since_view_magnitude = abs(
            float(features.since_view_return)
        )

        if preferences.time_horizon == "SHORT_TERM":
            # Short-term attention responds strongly to recent movement.
            # A 2% move since the user's baseline earns the full horizon
            # contribution.
            horizon_strength = min(
                since_view_magnitude / 0.02,
                1.0,
            )

            points = 5.0 * horizon_strength
            fit += points

            if points > 0:
                reasons.append(
                    AttentionReason(
                        type="PREFERENCE",
                        value="SHORT_TERM",
                        message=(
                            "Recent movement is especially relevant "
                            "to your short-term horizon"
                        ),
                    )
                )

        elif preferences.time_horizon == "LONG_TERM":
            # Long-term investors should be less sensitive to small recent
            # movements. The relevance ramps more slowly and reaches the
            # full contribution at a larger 5% accumulated move.
            horizon_strength = min(
                since_view_magnitude / 0.05,
                1.0,
            )

            points = 5.0 * horizon_strength
            fit += points

            if points > 0:
                reasons.append(
                    AttentionReason(
                        type="PREFERENCE",
                        value="LONG_TERM",
                        message=(
                            "The accumulated move since your last view "
                            "is relevant to your long-term horizon"
                        ),
                    )
                )

    return min(fit, 15.0), reasons


# ============================================================================
# TOTAL PERSONAL RELEVANCE
# ============================================================================


def calculate_personal_relevance(
    features: MarketFeatures,
    preferences: UserPreferences,
) -> tuple[float, list[AttentionReason]]:
    """
    Combine user-specific temporal context and explicit profile relevance.

    Components:

        since-last-view movement  0-20
        profile relevance         0-15
                                  ----
        Personal Relevance        0-35

    The API's historical field name `preference_fit` contains this combined
    value for backwards compatibility.
    """

    view_points, view_reason = calculate_since_view_points(
        features.since_view_return
    )

    profile_bonus, profile_reasons = calculate_preference_fit(
        features,
        preferences,
    )

    reasons: list[AttentionReason] = []

    if view_reason is not None:
        reasons.append(view_reason)

    reasons.extend(profile_reasons)

    personal_relevance = min(
        view_points + profile_bonus,
        35.0,
    )

    return personal_relevance, reasons


# ============================================================================
# FINAL ATTENTION SCORE
# ============================================================================


def classify_level(score: float) -> str:
    """
    Convert the numeric Attention Score into a simple attention band.
    """

    if score >= 80.0:
        return "HIGH"

    if score >= 50.0:
        return "MEDIUM"

    return "LOW"


def calculate_attention(
    features: MarketFeatures,
    preferences: UserPreferences,
) -> AttentionResult:
    """
    Calculate the complete Attention Score.

    Market Significance is computed independently from the user.

    Personal Relevance is then computed using:
    - the authenticated user's persisted last-view baseline
    - the authenticated user's explicit profile

    Final score is capped at 100.
    """

    objective_score, objective_reasons = calculate_objective_score(
        features
    )

    preference_fit, preference_reasons = calculate_personal_relevance(
        features,
        preferences,
    )

    final_score = min(
        objective_score + preference_fit,
        100.0,
    )

    level = classify_level(final_score)

    all_reasons = (
        objective_reasons
        + preference_reasons
    )

    return AttentionResult(
        objective_score=round(objective_score, 1),
        preference_fit=round(preference_fit, 1),
        final_score=round(final_score, 1),
        level=level,
        reasons=all_reasons,
    )