"""
JWT authentication utilities for AGRI-TECH.
Handles token creation and verification using python-jose.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.config import settings


def create_access_token(user_id: int, phone: str) -> str:
    """
    Create a JWT access token containing the user's ID and phone.

    Args:
        user_id: The database ID of the user.
        phone: The user's phone number.

    Returns:
        Encoded JWT string.
    """
    # Token payload with user identity and expiration
    expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),   # Subject: user ID as string (JWT convention)
        "phone": phone,         # Phone number for quick lookups
        "exp": expire,          # Expiration timestamp
    }
    # Sign the token with our secret key
    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.

    Args:
        token: The JWT string from the Authorization header.

    Returns:
        Decoded payload dict if valid, None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        phone: str = payload.get("phone")
        # Ensure required claims are present
        if user_id is None or phone is None:
            return None
        return {"user_id": int(user_id), "phone": phone}
    except JWTError:
        # Token is invalid, expired, or tampered with
        return None
