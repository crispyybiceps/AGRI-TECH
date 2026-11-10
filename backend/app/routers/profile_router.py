"""
Profile router for AGRI-TECH.
Allows authenticated users to view and update their profile.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import ProfileResponse, ProfileUpdateRequest
from app.dependencies import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get the authenticated user's profile.
    Requires a valid JWT in the Authorization header.
    """
    return current_user


@router.put("", response_model=ProfileResponse)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the authenticated user's profile (name and/or language preference).
    Only provided fields are updated; omitted fields remain unchanged.
    """
    # Update only the fields that were provided in the request
    if request.name is not None:
        current_user.name = request.name
    if request.language_preference is not None:
        current_user.language_preference = request.language_preference

    # Touch the updated_at timestamp
    current_user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(current_user)

    return current_user
