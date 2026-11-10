"""
Farm router for AGRI-TECH.
Full CRUD for farms, scoped to the currently authenticated user.
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Farm
from app.schemas import FarmCreateRequest, FarmUpdateRequest, FarmResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/farms", tags=["Farms"])


@router.post("", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
def create_farm(
    request: FarmCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new farm for the authenticated user.
    """
    farm = Farm(
        user_id=current_user.id,
        name=request.name,
        village=request.village,
        latitude=request.latitude,
        longitude=request.longitude,
        size_acres=request.size_acres,
        crops=request.crops,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("", response_model=List[FarmResponse])
def list_farms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all farms belonging to the authenticated user.
    """
    farms = db.query(Farm).filter(Farm.user_id == current_user.id).all()
    return farms


@router.get("/{farm_id}", response_model=FarmResponse)
def get_farm(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a single farm by ID.
    Returns 404 if the farm doesn't exist, 403 if it belongs to another user.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()

    # Farm doesn't exist at all
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )

    # Farm exists but belongs to a different user — forbidden
    if farm.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this farm",
        )

    return farm


@router.put("/{farm_id}", response_model=FarmResponse)
def update_farm(
    farm_id: int,
    request: FarmUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing farm. Only provided fields are modified.
    Returns 404 if not found, 403 if not owned by the current user.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()

    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )

    if farm.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this farm",
        )

    # Update only the fields that were explicitly provided
    if request.name is not None:
        farm.name = request.name
    if request.village is not None:
        farm.village = request.village
    if request.latitude is not None:
        farm.latitude = request.latitude
    if request.longitude is not None:
        farm.longitude = request.longitude
    if request.size_acres is not None:
        farm.size_acres = request.size_acres
    if request.crops is not None:
        farm.crops = request.crops

    # Touch the updated_at timestamp
    farm.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a farm by ID.
    Returns 404 if not found, 403 if not owned by the current user.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()

    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )

    if farm.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this farm",
        )

    db.delete(farm)
    db.commit()
    return None  # 204 No Content
