from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    risk_profile = Column(String, nullable=False, default="BALANCED")
    attention_style = Column(String, nullable=False, default="BALANCED")
    time_horizon = Column(String, nullable=False, default="LONG_TERM")
    version = Column(Integer, nullable=False, default=1)
    onboarding_completed = Column(Boolean, nullable=False, default=False, server_default="false")
