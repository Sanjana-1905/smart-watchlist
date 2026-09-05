from pydantic import BaseModel
from typing import Literal
from app.schemas.profile import RiskProfile, AttentionStyle, TimeHorizon

AttentionPriority = Literal["UPWARD_MOVEMENT", "DOWNSIDE_RISK", "BALANCED"]
MovementSensitivity = Literal["SELECTIVE", "BALANCED", "HIGH_MOVEMENT"]

class OnboardingIn(BaseModel):
    attention_priority: AttentionPriority
    movement_sensitivity: MovementSensitivity
    time_horizon: TimeHorizon

class OnboardingOut(BaseModel):
    risk_profile: RiskProfile
    attention_style: AttentionStyle
    time_horizon: TimeHorizon
    onboarding_completed: bool
