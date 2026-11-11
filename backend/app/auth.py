"""
JWT and Password authentication utilities for AGRI-TECH.
Uses passlib (pbkdf2_sha256 & bcrypt), JWT_SECRET (min 64 chars), and timezone-aware UTC datetime.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

# Password hashing context supporting pbkdf2_sha256 (standard) and bcrypt
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Verifies a plain password against the stored hash."""
    if not hashed_password or not plain_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generates a secure password hash."""
    return pwd_context.hash(password)


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
