"""
OTP delivery provider interface and implementations:
- MockProvider (development / fallback)
- TwilioProvider (Twilio SMS REST API)
- MSG91Provider (MSG91 Indian SMS Gateway)
"""

import logging
import urllib.request
import urllib.parse
import json
import base64
from abc import ABC, abstractmethod
from typing import Tuple
from app.config import settings

logger = logging.getLogger("agritech.otp")


class OTPDeliveryProvider(ABC):
    @abstractmethod
    def send_otp(self, phone: str, otp_code: str) -> Tuple[bool, str]:
        """
        Sends OTP to phone number.
        Returns: (success: bool, message: str)
        """
        pass


class MockOTPProvider(OTPDeliveryProvider):
    def send_otp(self, phone: str, otp_code: str) -> Tuple[bool, str]:
        print(f"\n==========================================")
        print(f" [MOCK OTP] Phone: {phone} | Code: {otp_code}")
        print(f" (In production, set OTP_PROVIDER=twilio or msg91)")
        print(f"==========================================\n")
        logger.info(f"[MOCK OTP] Delivered to console for {phone}")
        return True, "MOCK OTP delivered to console log"


class TwilioOTPProvider(OTPDeliveryProvider):
    def send_otp(self, phone: str, otp_code: str) -> Tuple[bool, str]:
        if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER):
            logger.warning("Twilio credentials incomplete, falling back to mock output")
            return MockOTPProvider().send_otp(phone, otp_code)

        # Standardize Indian phone number format
        to_phone = phone if phone.startswith("+") else f"+91{phone.strip()}"
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        
        body_text = f"Your AGRI-TECH verification code is: {otp_code}. Valid for 5 minutes. Do not share this OTP."
        payload = urllib.parse.urlencode({
            "From": settings.TWILIO_FROM_NUMBER,
            "To": to_phone,
            "Body": body_text
        }).encode("utf-8")

        auth_str = f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Authorization", f"Basic {b64_auth}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status in (200, 201):
                    logger.info(f"Twilio SMS sent to {to_phone}")
                    return True, "SMS sent successfully via Twilio"
                return False, f"Twilio returned status {resp.status}"
        except Exception as e:
            logger.error(f"Twilio SMS delivery failed: {e}")
            # Fall back to console print for resilience
            MockOTPProvider().send_otp(phone, otp_code)
            return True, f"Twilio failed ({e}); fallback OTP displayed in console"


class MSG91OTPProvider(OTPDeliveryProvider):
    def send_otp(self, phone: str, otp_code: str) -> Tuple[bool, str]:
        if not settings.MSG91_AUTH_KEY:
            logger.warning("MSG91 auth key missing, falling back to mock output")
            return MockOTPProvider().send_otp(phone, otp_code)

        # Indian phone number without leading +
        clean_phone = phone.replace("+", "").strip()
        if len(clean_phone) == 10:
            clean_phone = f"91{clean_phone}"

        url = "https://control.msg91.com/api/v5/otp"
        data = {
            "template_id": settings.MSG91_TEMPLATE_ID,
            "mobile": clean_phone,
            "authkey": settings.MSG91_AUTH_KEY,
            "otp": otp_code,
        }
        json_payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=json_payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("authkey", settings.MSG91_AUTH_KEY)

        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                res_body = json.loads(resp.read().decode("utf-8"))
                if res_body.get("type") == "success":
                    logger.info(f"MSG91 OTP sent to {clean_phone}")
                    return True, "SMS sent successfully via MSG91"
                return False, f"MSG91 error: {res_body.get('message')}"
        except Exception as e:
            logger.error(f"MSG91 SMS delivery failed: {e}")
            MockOTPProvider().send_otp(phone, otp_code)
            return True, f"MSG91 failed ({e}); fallback OTP displayed in console"


def get_otp_provider() -> OTPDeliveryProvider:
    provider = settings.OTP_PROVIDER
    if provider == "twilio":
        return TwilioOTPProvider()
    elif provider == "msg91":
        return MSG91OTPProvider()
    return MockOTPProvider()

