"""
Configuration module for AGRI-TECH backend.
Loads settings from environment variables via .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agritech.db")
    OTP_EXPIRY_MINUTES: int = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))
    ACCESS_TOKEN_EXPIRE_DAYS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
    ALGORITHM: str = "HS256"

    # Item 1: Real OTP Provider
    OTP_PROVIDER: str = os.getenv("OTP_PROVIDER", "mock").lower()  # "mock" | "twilio" | "msg91"
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
