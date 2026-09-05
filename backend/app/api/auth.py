import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import create_access_token
from app.core.current_user import get_current_user_id
from app.services import auth_service
from app.repositories import profile_repository
from app.schemas.auth import RegisterIn, LoginIn, TokenOut, UserOut
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    user, error = auth_service.register_user(db, payload.email, payload.password, payload.display_name)
    if error == "EMAIL_TAKEN":
        raise AppError(409, "EMAIL_TAKEN", "An account with this email already exists")
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password")
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    user = db.get(User, user_id)
    if not user:
        raise AppError(404, "USER_NOT_FOUND", "User not found")

    profile = profile_repository.get_for_user(db, user_id)
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        onboarding_completed=profile.onboarding_completed if profile else False,
    )
