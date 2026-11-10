"""
Weather and Advisory Router for AGRI-TECH.
Provides 7-day weather forecasts, cache-aware delivery for rural networks,
plain-language agricultural advisories, and seasonal crop recommendations.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Farm, User
from app.dependencies import get_current_user
from app.services.weather_service import (
    get_cached_or_fresh_weather,
    generate_agricultural_advisory,
    get_crop_recommendations,
    DEFAULT_MAHARASHTRA_LAT,
    DEFAULT_MAHARASHTRA_LNG,
    WEATHER_CODES
)

router = APIRouter(tags=["Weather & Advisory"])


@router.get("/weather/{farm_id}")
def get_farm_weather(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get 7-day weather forecast for a user's farm.
    Uses cached SQLite forecast if < 3 hours old.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    if farm.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this farm"
        )

    lat = farm.latitude or DEFAULT_MAHARASHTRA_LAT
    lng = farm.longitude or DEFAULT_MAHARASHTRA_LNG

    forecast = get_cached_or_fresh_weather(db, farm_id=farm.id, lat=lat, lng=lng)

    return {
        "farm_id": farm.id,
        "farm_name": farm.name,
        "village": farm.village,
        "latitude": lat,
        "longitude": lng,
        "weather_codes_map": WEATHER_CODES,
        **forecast
    }


@router.get("/advisory/{farm_id}")
def get_farm_advisory(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get rule-based agricultural advisories and seasonal crop suggestions
    tailored to the farm's forecast and standing crops.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    if farm.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this farm"
        )

    lat = farm.latitude or DEFAULT_MAHARASHTRA_LAT
    lng = farm.longitude or DEFAULT_MAHARASHTRA_LNG

    forecast = get_cached_or_fresh_weather(db, farm_id=farm.id, lat=lat, lng=lng)
    advisories = generate_agricultural_advisory(forecast, crops=farm.crops)
    crop_suggestions = get_crop_recommendations()

    return {
        "farm_id": farm.id,
        "farm_name": farm.name,
        "crops": farm.crops,
        "advisories": advisories,
        "crop_suggestions": crop_suggestions,
        "cached": forecast.get("cached", False),
        "cached_at": forecast.get("cached_at")
    }


@router.get("/weather-general")
def get_general_weather(
    lat: float = Query(DEFAULT_MAHARASHTRA_LAT),
    lng: float = Query(DEFAULT_MAHARASHTRA_LNG),
    db: Session = Depends(get_db),
):
    """
    General weather endpoint for quick checks without requiring a farm profile.
    """
    forecast = get_cached_or_fresh_weather(db, farm_id=None, lat=lat, lng=lng)
    return {
        "latitude": lat,
        "longitude": lng,
        "weather_codes_map": WEATHER_CODES,
        **forecast
    }

