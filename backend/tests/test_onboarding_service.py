"""
Pure mapping tests for onboarding_service.derive_profile — no DB, no client.
"""
from app.services.onboarding_service import OnboardingAnswers, derive_profile


def test_upward_movement_maps_to_momentum():
    result = derive_profile(OnboardingAnswers("UPWARD_MOVEMENT", "BALANCED", "SHORT_TERM"))
    assert result.attention_style == "MOMENTUM"


def test_downside_risk_maps_to_stability():
    result = derive_profile(OnboardingAnswers("DOWNSIDE_RISK", "BALANCED", "LONG_TERM"))
    assert result.attention_style == "STABILITY"


def test_balanced_attention_priority_maps_to_balanced():
    result = derive_profile(OnboardingAnswers("BALANCED", "BALANCED", "LONG_TERM"))
    assert result.attention_style == "BALANCED"


def test_selective_maps_to_conservative():
    result = derive_profile(OnboardingAnswers("BALANCED", "SELECTIVE", "LONG_TERM"))
    assert result.risk_profile == "CONSERVATIVE"


def test_high_movement_maps_to_aggressive():
    result = derive_profile(OnboardingAnswers("BALANCED", "HIGH_MOVEMENT", "SHORT_TERM"))
    assert result.risk_profile == "AGGRESSIVE"


def test_short_term_horizon_passes_through():
    result = derive_profile(OnboardingAnswers("BALANCED", "BALANCED", "SHORT_TERM"))
    assert result.time_horizon == "SHORT_TERM"


def test_long_term_horizon_passes_through():
    result = derive_profile(OnboardingAnswers("BALANCED", "BALANCED", "LONG_TERM"))
    assert result.time_horizon == "LONG_TERM"


def test_same_answers_always_derive_same_profile():
    answers = OnboardingAnswers("UPWARD_MOVEMENT", "HIGH_MOVEMENT", "SHORT_TERM")
    first = derive_profile(answers)
    second = derive_profile(answers)
    assert first == second
