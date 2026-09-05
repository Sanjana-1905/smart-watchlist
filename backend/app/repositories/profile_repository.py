from sqlalchemy.orm import Session
from app.models import UserProfile

def get_for_user(db: Session, user_id):
    return db.get(UserProfile, user_id)

def update_with_version(db: Session, user_id, expected_version, values: dict):
    profile = db.get(UserProfile, user_id)
    if profile is None:
        return None, "NOT_FOUND"
    if expected_version is not None and profile.version != expected_version:
        return None, "VERSION_CONFLICT"
    for key, value in values.items():
        setattr(profile, key, value)
    profile.version += 1
    db.commit()
    db.refresh(profile)
    return profile, None

def complete_onboarding(db: Session, user_id, values: dict):
    """
    Writes the derived profile and flips onboarding_completed to True.
    No If-Match check: this only ever fires once per user from the
    onboarding flow, not as a general-purpose concurrent edit path.
    """
    profile = db.get(UserProfile, user_id)
    if profile is None:
        return None
    for key, value in values.items():
        setattr(profile, key, value)
    profile.onboarding_completed = True
    profile.version += 1
    db.commit()
    db.refresh(profile)
    return profile
