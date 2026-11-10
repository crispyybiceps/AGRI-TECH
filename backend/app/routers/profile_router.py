"""
Profile router for AGRI-TECH.
Security Item 7: Users cannot escalate their role to 'admin' or 'transporter'.
Only allowed self-transitions: 'farmer' <-> 'buyer'.
Uses timezone-aware UTC datetime.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole
from app.schemas import ProfileResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    language_preference: Optional[str] = None
    role: Optional[str] = None


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("", response_model=ProfileResponse)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Security Item 7: Users cannot make themselves admin or transporter.
    Attempts to escalate role raise 403 Forbidden.
    """
    if request.role is not None:
        requested_role = request.role.lower().strip()
        # Disallow privilege escalation
        if requested_role in [UserRole.ADMIN.value, UserRole.TRANSPORTER.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Security violation: Users cannot self-assign the '{requested_role}' role."
            )
        if requested_role in [UserRole.FARMER.value, UserRole.BUYER.value]:
            current_user.role = requested_role

    if request.name is not None:
        current_user.name = request.name.strip()
    if request.language_preference is not None:
        current_user.language_preference = request.language_preference.strip()

    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)

    return current_user
