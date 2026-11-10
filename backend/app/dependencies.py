"""
FastAPI dependencies for AGRI-TECH.
Provides reusable dependency functions injected into route handlers.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import verify_access_token
from app.models import User

# HTTP Bearer scheme — extracts token from "Authorization: Bearer <token>" header
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that extracts and validates the JWT from the request,
    then returns the authenticated User object.

    Raises:
        HTTPException 401: If the token is missing, invalid, or expired.
        HTTPException 401: If the user in the token no longer exists.
    """
    token = credentials.credentials

    # Decode and verify the JWT
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch the user from the database
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found — account may have been deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
