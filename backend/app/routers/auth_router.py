"""
Authentication router for AGRI-TECH.
Security Item 6: OTPs hashed with HMAC-SHA256 using OTP_PEPPER.
Rate limiting: max 3 requests per phone per 10 minutes.
Max 5 verification attempts per OTP.
Uses timezone-aware UTC datetime.
"""

import random
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, OTP, UserRole
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


def hash_otp_hmac(phone: str, code: str) -> str:
    """
    Security Item 6: Hash OTPs with HMAC-SHA256 using OTP_PEPPER.
    """
    key = settings.OTP_PEPPER.encode("utf-8")
    message = f"{phone}:{code}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


@router.post("/send-otp", response_model=SendOTPResponse)
def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)):
    phone = request.phone.strip()

    now = datetime.now(timezone.utc)
    ten_min_ago = now - timedelta(minutes=10)

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
        role = UserRole.ADMIN.value if phone in settings.ADMIN_PHONES else UserRole.FARMER.value
        user = User(phone=phone, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Invalidate older active OTPs for this phone
    db.query(OTP).filter(OTP.phone == phone, OTP.is_used == False).update({"is_used": True})
    db.commit()

    # Generate 6-digit OTP code
    otp_code = str(random.randint(100000, 999999))
    hashed_code = hash_otp_hmac(phone, otp_code)

    otp_record = OTP(
        phone=phone,
        otp_code=hashed_code,
        created_at=now,
        expires_at=now + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
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
    phone = request.phone.strip()
    otp_input = request.otp.strip()

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

    now = datetime.now(timezone.utc)

    # Handle timezone-aware vs naive comparisons safely
    record_expires = otp_record.expires_at
    if record_expires.tzinfo is None:
        record_expires = record_expires.replace(tzinfo=timezone.utc)

    if otp_record.attempts >= MAX_VERIFY_ATTEMPTS:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum verification attempts exceeded. Please request a new OTP.",
        )

    if now > record_expires:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one.",
        )

    expected_hash = hash_otp_hmac(phone, otp_input)
    if not hmac.compare_digest(otp_record.otp_code, expected_hash):
        otp_record.attempts += 1
        db.commit()
        remaining = MAX_VERIFY_ATTEMPTS - otp_record.attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {remaining} attempt(s) remaining.",
        )

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
