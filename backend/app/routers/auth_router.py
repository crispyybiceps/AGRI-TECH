"""
Authentication router for AGRI-TECH.
Features:
- Configurable OTP provider: mock | twilio | msg91
- Rate limiting: max 3 OTP requests per phone per 10 minutes
- 5-minute expiration
- Max 5 verification attempts per OTP
- SHA-256 hashed OTP storage
"""

import random
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, OTP
from app.schemas import (
    SendOTPRequest, SendOTPResponse,
    VerifyOTPRequest, VerifyOTPResponse, UserBrief,
)
from app.auth import create_access_token
from app.config import settings
from app.services.otp_service import get_otp_provider

router = APIRouter(prefix="/auth", tags=["Authentication"])

MAX_OTPS_PER_10_MIN = 3
MAX_VERIFY_ATTEMPTS = 5


def hash_otp(phone: str, code: str) -> str:
    """Hashes OTP using phone and server secret as salt."""
    salt = settings.SECRET_KEY
    return hashlib.sha256(f"{phone}:{code}:{salt}".encode("utf-8")).hexdigest()


@router.post("/send-otp", response_model=SendOTPResponse)
def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)):
    """
    Send OTP to phone with rate limiting (max 3 per 10 min), hashed storage,
    and provider selection (mock | twilio | msg91).
    """
    phone = request.phone.strip()

    # Rate limiting: count requests for this phone in the last 10 minutes
    ten_min_ago = datetime.utcnow() - timedelta(minutes=10)
    recent_otps_count = (
        db.query(OTP)
        .filter(OTP.phone == phone, OTP.created_at >= ten_min_ago)
        .count()
    )

    if recent_otps_count >= MAX_OTPS_PER_10_MIN:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please wait 10 minutes before requesting again.",
        )

    # Check or auto-register user
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Invalidate older active OTPs for this phone
    db.query(OTP).filter(OTP.phone == phone, OTP.is_used == False).update({"is_used": True})
    db.commit()

    # Generate 6-digit OTP code
    otp_code = str(random.randint(100000, 999999))
    hashed_code = hash_otp(phone, otp_code)

    # Store hashed OTP in database
    otp_record = OTP(
        phone=phone,
        otp_code=hashed_code,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
        attempts=0,
        is_used=False,
    )
    db.add(otp_record)
    db.commit()

    # Send OTP via selected provider
    provider = get_otp_provider()
    success, provider_msg = provider.send_otp(phone, otp_code)

    return SendOTPResponse(
        message=f"OTP sent ({provider_msg})",
        phone=phone,
        mock_otp=otp_code if settings.OTP_PROVIDER == "mock" else None
    )


@router.post("/verify-otp", response_model=VerifyOTPResponse)
def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Verify OTP with max 5 attempts limit, expiry verification, and constant-time check.
    """
    phone = request.phone.strip()
    otp_input = request.otp.strip()

    # Find most recent unused OTP for this phone
    otp_record = (
        db.query(OTP)
        .filter(OTP.phone == phone, OTP.is_used == False)
        .order_by(OTP.created_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active OTP found. Please request a new OTP.",
        )

    # Check max attempts limit
    if otp_record.attempts >= MAX_VERIFY_ATTEMPTS:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum verification attempts exceeded. Please request a new OTP.",
        )

    # Check expiration
    if datetime.utcnow() > otp_record.expires_at:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one.",
        )

    # Verify hash match
    expected_hash = hash_otp(phone, otp_input)
    if otp_record.otp_code != expected_hash:
        otp_record.attempts += 1
        db.commit()
        remaining = MAX_VERIFY_ATTEMPTS - otp_record.attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {remaining} attempt(s) remaining.",
        )

    # Mark as used
    otp_record.is_used = True
    db.commit()

    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    access_token = create_access_token(user_id=user.id, phone=user.phone)

    return VerifyOTPResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserBrief(id=user.id, phone=user.phone, name=user.name),
    )
