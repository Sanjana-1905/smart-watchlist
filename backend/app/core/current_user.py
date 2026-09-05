import uuid
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import decode_access_token
from app.core.errors import AppError

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> uuid.UUID:
    if credentials is None:
        raise AppError(401, "MISSING_TOKEN", "Authentication required")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise AppError(401, "INVALID_TOKEN", "Invalid or expired token")

    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise AppError(401, "INVALID_TOKEN", "Invalid or expired token")
