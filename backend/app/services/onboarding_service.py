from dataclasses import dataclass


@dataclass
class OnboardingAnswers:
    attention_priority: str      # UPWARD_MOVEMENT | DOWNSIDE_RISK | BALANCED
    movement_sensitivity: str    # SELECTIVE | BALANCED | HIGH_MOVEMENT
    time_horizon: str            # SHORT_TERM | LONG_TERM


@dataclass
class DerivedProfile:
    risk_profile: str
    attention_style: str
    time_horizon: str


_STYLE_MAP = {
    "UPWARD_MOVEMENT": "MOMENTUM",
    "DOWNSIDE_RISK": "STABILITY",
    "BALANCED": "BALANCED",
}

_RISK_MAP = {
    "SELECTIVE": "CONSERVATIVE",
    "BALANCED": "BALANCED",
    "HIGH_MOVEMENT": "AGGRESSIVE",
}

_HORIZON_MAP = {
    "SHORT_TERM": "SHORT_TERM",
    "LONG_TERM": "LONG_TERM",
}


def derive_profile(answers: OnboardingAnswers) -> DerivedProfile:
    return DerivedProfile(
        attention_style=_STYLE_MAP[answers.attention_priority],
        risk_profile=_RISK_MAP[answers.movement_sensitivity],
        time_horizon=_HORIZON_MAP[answers.time_horizon],
    )
