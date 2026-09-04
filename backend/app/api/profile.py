import uuid
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.current_user import get_current_user_id
from app.repositories import profile_repository
from app.schemas.profile import ProfileOut, ProfileUpdateIn

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    profile = profile_repository.get_for_user(db, user_id)
    if not profile:
        raise AppError(404, "PROFILE_NOT_FOUND", "No profile found for user")
    return profile

@router.put("", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdateIn,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
    if_match: int | None = Header(default=None, alias="If-Match"),
):
    profile, error = profile_repository.update_with_version(
        db, user_id, if_match,
        {
            "risk_profile": payload.risk_profile,
            "attention_style": payload.attention_style,
            "time_horizon": payload.time_horizon,
        },
    )
    if error == "NOT_FOUND":
        raise AppError(404, "PROFILE_NOT_FOUND", "No profile found for user")
    if error == "VERSION_CONFLICT":
        raise AppError(409, "VERSION_CONFLICT", "Profile was updated by another request")
    return profile
