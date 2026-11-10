"""
FastAPI dependencies for AGRI-TECH.
Provides user authentication and strict admin verification.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import verify_access_token
from app.models import User, UserRole
from app.config import settings

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Extracts and validates JWT, returns User object."""
    token = credentials.credentials
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Sync admin status if phone is in ADMIN_PHONES
    if user.phone in settings.ADMIN_PHONES and user.role != UserRole.ADMIN.value:
        user.role = UserRole.ADMIN.value
        db.commit()

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Security Item 1: Admin endpoints require a require_admin check.
    Admin is set only through ADMIN_PHONES env var.
    """
    # Check phone list or confirmed admin role
    is_admin_phone = current_user.phone in settings.ADMIN_PHONES
    if not (is_admin_phone or current_user.role == UserRole.ADMIN.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Administrator privileges required.",
        )
    return current_user
