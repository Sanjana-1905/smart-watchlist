import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User, UserProfile
from app.core.security import hash_password, verify_password


def register_user(db: Session, email: str, password: str, display_name: str | None):
    """Returns (user, None) on success or (None, 'EMAIL_TAKEN') on duplicate email."""
    user = User(
        id=uuid.uuid4(),
        email=email.lower(),
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return None, "EMAIL_TAKEN"

    db.add(UserProfile(
        user_id=user.id,
        risk_profile="BALANCED",
        attention_style="BALANCED",
        time_horizon="LONG_TERM",
        version=1,
    ))
    db.commit()
    db.refresh(user)
    return user, None


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Returns the User on valid credentials, else None. Never reveals which check failed."""
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
