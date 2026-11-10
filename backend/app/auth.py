"""
JWT authentication utilities for AGRI-TECH.
Uses JWT_SECRET (min 64 chars) and timezone-aware UTC datetime.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from app.config import settings


def create_access_token(user_id: int, phone: str) -> str:
    """Creates signed JWT with user ID, phone, and expiration."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "phone": phone,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    """Decodes and verifies a JWT access token using JWT_SECRET."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        phone: str = payload.get("phone")
        if user_id is None or phone is None:
            return None
        return {"user_id": int(user_id), "phone": phone}
    except JWTError:
        return None
