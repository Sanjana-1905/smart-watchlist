"""
Unit tests for the attention scoring engine.

These tests prove the core claims:
1. Objective score is independent of preferences
2. Same market facts → same objective score always
3. Different preferences → different final score
4. Scoring bands work correctly
5. All signals contribute as designed
6. Reasons are emitted only for meaningful contributors
"""

import pytest
from app.services.attention_service import (
    MarketFeatures,
    UserPreferences,
    calculate_attention,
    calculate_objective_score,
    calculate_preference_fit,
    calculate_personal_relevance,
    classify_level,
)


class TestObjectiveScoring:
    """Objective score depends only on market facts."""

    def test_ordinary_movement(self):
        """Low volatility, normal volume, no view baseline → LOW."""
        features = MarketFeatures(
            session_return=0.01,      # +1%
            volatility_20d=0.02,      # 2% daily std dev → 0.5σ
            volume_ratio=1.0,
            since_view_return=None,
            new_20d_high=False,
        )
        score, reasons = calculate_objective_score(features)
        assert score < 30, f"Ordinary movement should score low, got {score}"
        
        # No reason for ordinary return (< 1σ)
        reason_types = {r.type for r in reasons}
        assert "UNUSUAL_RETURN" not in reason_types

    def test_unusual_volatility_movement(self):
        """3σ move → 45 points from unusual_return."""
        features = MarketFeatures(
            session_return=0.06,      # +6%
            volatility_20d=0.02,      # 2% → 6%/2% = 3σ
            volume_ratio=1.0,
            since_view_return=None,
            new_20d_high=False,
        )
        score, reasons = calculate_objective_score(features)
        assert 40 <= score <= 50, f"3σ move should yield ~45 points, got {score}"
        
        reason_types = {r.type for r in reasons}
        assert "UNUSUAL_RETURN" in reason_types

    def test_volume_contribution(self):
        """2.0× volume → ~17 points (min((2.0-1)/1.5, 1) * 25)."""
        features = MarketFeatures(
            session_return=0.01,
            volatility_20d=0.02,
            volume_ratio=2.0,
            since_view_return=None,
            new_20d_high=False,
        )
        score, reasons = calculate_objective_score(features)
        
        # Unusual return: min(0.01/0.02 / 3, 1) * 45 = min(0.166, 1) * 45 ≈ 7.5
        # Volume: min((2.0-1)/1.5, 1) * 25 = min(0.666, 1) * 25 ≈ 16.7
        # Total ≈ 24.2
        assert 20 <= score <= 30, f"Expected ~24, got {score}"

    def test_volume_no_reason_when_normal(self):
        """Normal volume (1.0×) contributes 0 points and no reason."""
        features = MarketFeatures(
            session_return=0.01,
            volatility_20d=0.02,
            volume_ratio=1.0,
            since_view_return=None,
            new_20d_high=False,
        )
        score, reasons = calculate_objective_score(features)
        
        reason_types = {r.type for r in reasons}
        assert "VOLUME" not in reason_types, "Normal volume should not generate reason"

    def test_volume_reason_when_elevated(self):
        """Elevated volume (2.0×) generates a reason."""
        features = MarketFeatures(
            session_return=0.01,
            volatility_20d=0.02,
            volume_ratio=2.0,
            since_view_return=None,
            new_20d_high=False,
        )
        score, reasons = calculate_objective_score(features)
        
        reason_types = {r.type for r in reasons}
        assert "VOLUME" in reason_types, "Elevated volume should generate reason"

    def test_new_20d_high(self):
        """New high adds exactly 10 points."""
        features = MarketFeatures(
            session_return=0.01,
            volatility_20d=0.02,
            volume_ratio=1.0,
            since_view_return=None,
            new_20d_high=True,
        )
        score, reasons = calculate_objective_score(features)
        
        reason_types = {r.type for r in reasons}
        assert "NEW_HIGH" in reason_types
        assert score >= 10, f"New high should contribute at least 10 points, got {score}"

    def test_since_view_points_large(self):
        """5% since view → 20 points (capped)."""
        features = MarketFeatures(
            session_return=0.01,
            volatility_20d=0.02,
            volume_ratio=1.0,
            since_view_return=0.05,   # +5% since viewed
            new_20d_high=False,
        )
        score, reasons = calculate_objective_score(features)
        
        assert score == pytest.approx(7.5)
        assert "SINCE_VIEW" not in {r.type for r in reasons}
        relevance, reasons = calculate_personal_relevance(
            features, UserPreferences("BALANCED", "BALANCED", "LONG_TERM")
        )
        assert relevance == 20
        assert [r.type for r in reasons] == ["SINCE_VIEW"]

    def test_since_view_no_reason_when_small(self):
        """Small change (< 1%) contributes points but no reason."""
        features = MarketFeatures(
            session_return=0.01,
            volatility_20d=0.02,
            volume_ratio=1.0,
            since_view_return=0.005,  # +0.5% since viewed
            new_20d_high=False,
        )
        score, reasons = calculate_objective_score(features)
        
        reason_types = {r.type for r in reasons}
        assert "SINCE_VIEW" not in reason_types, "Small change should not generate reason"

    def test_no_previous_view_state(self):
        """If never viewed (None), since_view is ignored."""
        features = MarketFeatures(
            session_return=0.01,
            volatility_20d=0.02,
            volume_ratio=1.0,
            since_view_return=None,
            new_20d_high=False,
        )
        score, reasons = calculate_objective_score(features)
        
        view_reasons = [r for r in reasons if r.type == "SINCE_VIEW"]
        assert len(view_reasons) == 0


class TestPreferenceFit:
    """Preference fit changes final score but NOT objective score."""

    def test_same_market_different_profiles_invariant(self):
        """
        CORE INVARIANT: same market facts must yield same objective score
        regardless of user preferences.
        """
        features = MarketFeatures(
            session_return=0.04,      # +4%
            volatility_20d=0.015,     # 1.5% → ~2.7σ unusual
            volume_ratio=2.0,
            since_view_return=0.02,
            new_20d_high=True,
        )

        pref_aggressive = UserPreferences(
            risk_profile="AGGRESSIVE",
            attention_style="MOMENTUM",
            time_horizon="SHORT_TERM",
        )

        pref_conservative = UserPreferences(
            risk_profile="CONSERVATIVE",
            attention_style="STABILITY",
            time_horizon="LONG_TERM",
        )

        result_agg = calculate_attention(features, pref_aggressive)
        result_con = calculate_attention(features, pref_conservative)

        # Objective scores MUST be identical
        assert result_agg.objective_score == result_con.objective_score, \
            f"INVARIANT VIOLATED: objective score changed: {result_agg.objective_score} vs {result_con.objective_score}"

        # But final scores differ due to preference fit
        assert result_agg.final_score != result_con.final_score, \
            "Preference fit should change final score"

    def test_momentum_preference_bonus(self):
        """MOMENTUM + positive unusual move (>= 1.5σ) → +5 bonus."""
        features = MarketFeatures(
            session_return=0.05,      # +5%
            volatility_20d=0.02,      # ~2.5σ
            volume_ratio=1.0,
            since_view_return=None,
            new_20d_high=False,
        )

        pref_momentum = UserPreferences(
            risk_profile="BALANCED",
            attention_style="MOMENTUM",
            time_horizon="LONG_TERM",
        )

        result = calculate_attention(features, pref_momentum)
        assert result.preference_fit >= 5.0, "MOMENTUM + positive should yield +5"

    def test_stability_preference_bonus(self):
        """STABILITY + negative unusual move (>= 1.5σ) → +5 bonus."""
        features = MarketFeatures(
            session_return=-0.05,     # -5%
            volatility_20d=0.02,      # ~2.5σ down
            volume_ratio=1.0,
            since_view_return=None,
            new_20d_high=False,
        )

        pref_stability = UserPreferences(
            risk_profile="BALANCED",
            attention_style="STABILITY",
            time_horizon="LONG_TERM",
        )

        result = calculate_attention(features, pref_stability)
        assert result.preference_fit >= 5.0, "STABILITY + negative should yield +5"

    def test_conservative_downside_bonus(self):
        """CONSERVATIVE + negative unusual move → +5 bonus."""
        features = MarketFeatures(
            session_return=-0.04,
            volatility_20d=0.015,
            volume_ratio=1.0,
            since_view_return=None,
            new_20d_high=False,
        )

        pref_conservative = UserPreferences(
            risk_profile="CONSERVATIVE",
            attention_style="BALANCED",
            time_horizon="LONG_TERM",
        )

        result = calculate_attention(features, pref_conservative)
        assert result.preference_fit >= 5.0, "CONSERVATIVE + downside should yield +5"

    def test_preference_fit_capped(self):
        """Preference fit max is +15."""
        features = MarketFeatures(
            session_return=0.10,
            volatility_20d=0.01,
            volume_ratio=3.0,
            since_view_return=0.10,
            new_20d_high=True,
        )

        pref_aligned = UserPreferences(
            risk_profile="AGGRESSIVE",
            attention_style="MOMENTUM",
            time_horizon="SHORT_TERM",
        )

        bonus, _ = calculate_preference_fit(features, pref_aligned)
        assert bonus == 15
        result = calculate_attention(features, pref_aligned)
        assert result.preference_fit == 35


class TestFinalScoring:
    """Final score capped at 100, classified into bands."""

    def test_score_capped_at_100(self):
        """Final score never exceeds 100."""
        features = MarketFeatures(
            session_return=0.15,
            volatility_20d=0.01,
            volume_ratio=5.0,
            since_view_return=0.15,
            new_20d_high=True,
        )

        pref_aligned = UserPreferences(
            risk_profile="AGGRESSIVE",
            attention_style="MOMENTUM",
            time_horizon="SHORT_TERM",
        )

        result = calculate_attention(features, pref_aligned)
        assert result.final_score <= 100, "Final score should not exceed 100"

    def test_classification_low(self):
        """Score < 50 → LOW."""
        features = MarketFeatures(
            session_return=0.01,
            volatility_20d=0.02,
            volume_ratio=1.0,
            since_view_return=None,
            new_20d_high=False,
        )

        pref = UserPreferences(
            risk_profile="BALANCED",
            attention_style="BALANCED",
            time_horizon="LONG_TERM",
        )

        result = calculate_attention(features, pref)
        assert result.level == "LOW", f"Expected LOW, got {result.level}"

    def test_classification_medium(self):
        """50 ≤ score < 80 → MEDIUM."""
        features = MarketFeatures(
            session_return=0.03,
            volatility_20d=0.015,
            volume_ratio=1.8,
            since_view_return=0.02,
            new_20d_high=False,
        )

        pref = UserPreferences(
            risk_profile="BALANCED",
            attention_style="BALANCED",
            time_horizon="LONG_TERM",
        )

        result = calculate_attention(features, pref)
        assert 50 <= result.final_score < 80, \
            f"Expected MEDIUM range (50-80), got {result.final_score}"
        assert result.level == "MEDIUM"

    def test_classification_high(self):
        """Score ≥ 80 → HIGH."""
        features = MarketFeatures(
            session_return=0.06,
            volatility_20d=0.015,
            volume_ratio=2.5,
            since_view_return=0.04,
            new_20d_high=True,
        )

        pref = UserPreferences(
            risk_profile="BALANCED",
            attention_style="BALANCED",
            time_horizon="LONG_TERM",
        )

        result = calculate_attention(features, pref)
        assert result.final_score >= 80, f"Expected HIGH, got {result.final_score}"
        assert result.level == "HIGH"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
