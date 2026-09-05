from pydantic import BaseModel
from typing import Literal

RiskProfile = Literal["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]
AttentionStyle = Literal["MOMENTUM", "STABILITY", "BALANCED"]
TimeHorizon = Literal["SHORT_TERM", "LONG_TERM"]

class ProfileOut(BaseModel):
    risk_profile: RiskProfile
    attention_style: AttentionStyle
    time_horizon: TimeHorizon
    version: int
    onboarding_completed: bool

    class Config:
        from_attributes = True

class ProfileUpdateIn(BaseModel):
    risk_profile: RiskProfile
    attention_style: AttentionStyle
    time_horizon: TimeHorizon
