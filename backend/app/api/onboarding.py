import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.current_user import get_current_user_id
from app.repositories import profile_repository
from app.schemas.onboarding import OnboardingIn, OnboardingOut
from app.services.onboarding_service import OnboardingAnswers, derive_profile

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("", response_model=OnboardingOut)
def complete_onboarding(
    payload: OnboardingIn,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    derived = derive_profile(OnboardingAnswers(
        attention_priority=payload.attention_priority,
        movement_sensitivity=payload.movement_sensitivity,
        time_horizon=payload.time_horizon,
    ))

    profile = profile_repository.complete_onboarding(
        db, user_id,
        {
            "risk_profile": derived.risk_profile,
            "attention_style": derived.attention_style,
            "time_horizon": derived.time_horizon,
        },
    )
    if profile is None:
        raise AppError(404, "PROFILE_NOT_FOUND", "No profile found for user")

    return OnboardingOut(
        risk_profile=profile.risk_profile,
        attention_style=profile.attention_style,
        time_horizon=profile.time_horizon,
        onboarding_completed=profile.onboarding_completed,
    )
