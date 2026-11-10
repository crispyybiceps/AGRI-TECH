"""
Configuration module for AGRI-TECH backend.
Loads settings from environment variables via .env file.
Enforces security requirements for secrets and origins.
"""

import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Security - Item 6: JWT_SECRET & OTP_PEPPER required with >= 64 chars
    # We check JWT_SECRET first, falling back to SECRET_KEY for compatibility
    _raw_jwt_secret = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY", "")
    _raw_otp_pepper = os.getenv("OTP_PEPPER", "")

    # For safety during initial boots or tests, if missing or < 64, provide or validate
    if not _raw_jwt_secret or len(_raw_jwt_secret) < 64:
        # If in strict mode we raise error; we enforce min 64 chars
        if os.getenv("TESTING") != "true" and os.getenv("ENV") == "production":
            raise ValueError("JWT_SECRET must be set and at least 64 characters long.")
        # Ensure at least 64 chars fallback for dev if empty
        if not _raw_jwt_secret:
            _raw_jwt_secret = "default-development-jwt-secret-key-that-must-be-at-least-64-characters-long-for-hmac-sha256-security"

    if not _raw_otp_pepper or len(_raw_otp_pepper) < 64:
        if os.getenv("TESTING") != "true" and os.getenv("ENV") == "production":
            raise ValueError("OTP_PEPPER must be set and at least 64 characters long.")
        if not _raw_otp_pepper:
            _raw_otp_pepper = "default-development-otp-pepper-secret-must-be-at-least-64-characters-long-for-secure-otp-hashing"

    JWT_SECRET: str = _raw_jwt_secret
    SECRET_KEY: str = _raw_jwt_secret  # Backwards compatibility alias
    OTP_PEPPER: str = _raw_otp_pepper

    # Database URL with automatic Postgres URL encoding & dialect mapping
    _raw_db_url = os.getenv("DATABASE_URL", "sqlite:///./agritech.db")

    # If postgresql:// without driver, ensure postgresql+psycopg2://
    if _raw_db_url.startswith("postgresql://"):
        _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # Automatically fix unencoded @ in password if present in postgres URLs
    # Format: postgresql+psycopg2://user:pass@host:port/dbname
    if "postgresql+psycopg2://" in _raw_db_url and _raw_db_url.count("@") > 1:
        try:
            prefix = "postgresql+psycopg2://"
            rest = _raw_db_url[len(prefix):]
            last_at = rest.rfind("@")
            user_pass = rest[:last_at]
            host_part = rest[last_at + 1:]
            if ":" in user_pass:
                user, password = user_pass.split(":", 1)
                encoded_pass = urllib.parse.quote_plus(password)
                _raw_db_url = f"{prefix}{user}:{encoded_pass}@{host_part}"
        except Exception:
            pass

    DATABASE_URL: str = _raw_db_url

    OTP_EXPIRY_MINUTES: int = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))
    ACCESS_TOKEN_EXPIRE_DAYS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
    ALGORITHM: str = "HS256"

    # Item 1: Admin configuration
    # Comma-separated list of admin phone numbers e.g. "9999999999,+919999999999"
    ADMIN_PHONES: list = [
        p.strip() for p in os.getenv("ADMIN_PHONES", "9999999999,+919999999999").split(",") if p.strip()
    ]

    # Item 10: CORS Allowed Origins
    ALLOWED_ORIGINS: list = [
        o.strip() for o in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,https://agri-tech-sarvesh.vercel.app,http://localhost:3000"
        ).split(",") if o.strip()
    ]

    # Item 1: Real OTP Provider
    OTP_PROVIDER: str = os.getenv("OTP_PROVIDER", "mock").lower()
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")
    MSG91_AUTH_KEY: str = os.getenv("MSG91_AUTH_KEY", "")
    MSG91_SENDER_ID: str = os.getenv("MSG91_SENDER_ID", "AGRITC")
    MSG91_TEMPLATE_ID: str = os.getenv("MSG91_TEMPLATE_ID", "")

    # Item 2: Weather Debug Flag
    DEBUG_MOCK: bool = os.getenv("DEBUG_MOCK", "false").lower() in ("true", "1", "yes")

    # Item 3 & 6: Claude AI (Anthropic)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    # Item 7: Agmarknet Mandi Data.gov.in
    DATA_GOV_API_KEY: str = os.getenv("DATA_GOV_API_KEY", "")
    AGMARKNET_RESOURCE_ID: str = os.getenv("AGMARKNET_RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070")

    # Item 9: Razorpay Payment Gateway (Test Mode)
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")


settings = Settings()
