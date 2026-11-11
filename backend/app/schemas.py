"""
Pydantic schemas for AGRI-TECH API request/response validation.
These define the shape of data flowing in and out of the API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Auth Schemas
# ──────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    """Request body for sending an OTP to a phone number."""
    phone: str = Field(..., min_length=10, max_length=15, description="Indian mobile number")


class SendOTPResponse(BaseModel):
    """Response after OTP is sent (or mock-generated)."""
    message: str
    phone: str
    mock_otp: Optional[str] = None  # Returned in development mode so user can see it on screen


class VerifyOTPRequest(BaseModel):
    """Request body for verifying an OTP."""
    phone: str = Field(..., min_length=10, max_length=15)
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class UserBrief(BaseModel):
    """Minimal user info returned after auth."""
    id: int
    phone: str
    name: Optional[str] = None

    class Config:
        from_attributes = True  # Pydantic v2: allows creation from ORM objects


class VerifyOTPResponse(BaseModel):
    """Response after successful OTP verification — includes JWT."""
    access_token: str
    token_type: str = "bearer"
    user: UserBrief


class SignupRequest(BaseModel):
    """Request body for user registration."""
    phone: str = Field(..., min_length=10, max_length=15, description="Mobile number")
    password: str = Field(..., min_length=4, max_length=100, description="User password")
    name: Optional[str] = Field(None, max_length=200, description="Full name")


class LoginRequest(BaseModel):
    """Request body for user login."""
    phone: str = Field(..., min_length=10, max_length=15, description="Mobile number")
    password: str = Field(..., min_length=1, max_length=100, description="User password")


class AuthResponse(BaseModel):
    """Unified authentication response containing JWT and user profile brief."""
    access_token: str
    token_type: str = "bearer"
    user: UserBrief


# ──────────────────────────────────────────────
# Profile Schemas
# ──────────────────────────────────────────────

class ProfileResponse(BaseModel):
    """Full user profile response."""
    id: int
    phone: str
    name: Optional[str] = None
    language_preference: str
    role: str = "farmer"
    is_verified: bool = False
    rating: float = 5.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileUpdateRequest(BaseModel):
    """Request body for updating user profile fields."""
    name: Optional[str] = None
    language_preference: Optional[str] = None


# ──────────────────────────────────────────────
# Farm Schemas
# ──────────────────────────────────────────────

class FarmCreateRequest(BaseModel):
    """Request body for creating a new farm."""
    name: str = Field(..., min_length=1, max_length=200)
    village: str = Field(..., min_length=1, max_length=200)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    size_acres: float = Field(..., gt=0, description="Farm size in acres, must be positive")
    crops: Optional[str] = None  # Comma-separated crop names


class FarmUpdateRequest(BaseModel):
    """Request body for updating an existing farm. All fields optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    village: Optional[str] = Field(None, min_length=1, max_length=200)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    size_acres: Optional[float] = Field(None, gt=0)
    crops: Optional[str] = None


class FarmResponse(BaseModel):
    """Farm data returned from the API."""
    id: int
    user_id: int
    name: str
    village: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    size_acres: float
    crops: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
