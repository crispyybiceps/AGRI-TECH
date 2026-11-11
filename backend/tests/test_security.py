"""
Security and Integration Tests for AGRI-TECH
Validates Part 2 Security Requirements:
1. Admin endpoints require require_admin check (ADMIN_PHONES env var).
2. Payment verify and webhook verify Razorpay signatures (HMAC-SHA256, hmac.compare_digest). Never mark paid without valid signature.
3. Without Razorpay keys, create clearly labeled demo orders that cannot be marked paid.
4. Sensor endpoint: require a valid device key (X-Device-Key), reject unregistered devices (401), validate value ranges.
5. Offers and transport: use enums, only seller can accept an offer, buyer cannot confirm their own offer, only transporters can accept jobs.
6. JWT_SECRET and OTP_PEPPER required env vars >= 64 chars. Hash OTPs with HMAC-SHA256 and pepper.
7. Users cannot make themselves admin or transporter.
8. Replace datetime.utcnow() with datetime.now(timezone.utc).
9. Restrict CORS to ALLOWED_ORIGINS.
"""

import pytest
import hmac
import hashlib
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import (
    User, Farm, Listing, Offer, TransportRequest, PaymentOrder,
    SensorDevice, SensorReading, OfferStatus, TransportStatus, PaymentStatus, UserRole
)
from app.auth import create_access_token
from app.config import settings
from app.routers.auth_router import hash_otp_hmac


def create_test_user(db, phone: str, role: str = "farmer"):
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone, name="Test User", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.role = role
        db.commit()
    token = create_access_token(user_id=user.id, phone=user.phone)
    return user, token


# ──────────────────────────────────────────────
# 1. Admin Endpoints require require_admin (ADMIN_PHONES)
# ──────────────────────────────────────────────
def test_admin_endpoints_require_admin_role(client, db):
    # Non-admin farmer
    farmer, farmer_token = create_test_user(db, "9870000001", role=UserRole.FARMER.value)
    res = client.get("/admin/analytics", headers={"Authorization": f"Bearer {farmer_token}"})
    assert res.status_code == 403
    assert "Administrator privileges required" in res.json()["detail"]

    # Admin phone from settings.ADMIN_PHONES
    admin_phone = settings.ADMIN_PHONES[0]
    admin, admin_token = create_test_user(db, admin_phone, role=UserRole.ADMIN.value)
    res_admin = client.get("/admin/analytics", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    assert "users" in res_admin.json()


# ──────────────────────────────────────────────
# 2. Razorpay Signature Verification & No Mark Paid without Signature
# ──────────────────────────────────────────────
def test_razorpay_signature_verification_and_protection(client, db):
    user, token = create_test_user(db, "9870000002")
    listing = Listing(farmer_id=user.id, crop="Soybean", quantity_quintals=5, expected_price=4500, location="Pune")
    db.add(listing)
    db.commit()

    offer = Offer(listing_id=listing.id, buyer_id=user.id, offered_price=4400, quantity=5, status=OfferStatus.CONFIRMED.value)
    db.add(offer)
    db.commit()

    # Create real order with secret key
    secret = "test_razorpay_secret_key_12345"
    with pytest.MonkeyPatch.context() as m:
        m.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_real")
        m.setattr(settings, "RAZORPAY_KEY_SECRET", secret)

        order_res = client.post("/marketplace/payments/create-order", headers={"Authorization": f"Bearer {token}"}, json={"offer_id": offer.id})
        assert order_res.status_code == 201
        order_data = order_res.json()
        order_id = order_data["payment_order_id"]
        rzp_order_id = order_data["razorpay_order_id"]

        # Attempt verify with INVALID signature
        bad_sig_res = client.post("/marketplace/payments/verify", json={
            "order_id": order_id,
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": "pay_test_001",
            "razorpay_signature": "invalid_forged_signature"
        })
        assert bad_sig_res.status_code == 400
        assert "Invalid Razorpay payment signature" in bad_sig_res.json()["detail"]

        # Attempt verify with VALID HMAC-SHA256 signature
        msg = f"{rzp_order_id}|pay_test_001".encode("utf-8")
        valid_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        valid_res = client.post("/marketplace/payments/verify", json={
            "order_id": order_id,
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": "pay_test_001",
            "razorpay_signature": valid_sig
        })
        assert valid_res.status_code == 200
        assert valid_res.json()["status"] == PaymentStatus.PAID.value


# ──────────────────────────────────────────────
# 3. Without Razorpay Keys -> Clearly Labeled Demo Orders Cannot be Marked Paid
# ──────────────────────────────────────────────
def test_demo_orders_without_keys_cannot_be_paid(client, db):
    user, token = create_test_user(db, "9870000003")
    listing = Listing(farmer_id=user.id, crop="Onion", quantity_quintals=10, expected_price=2000, location="Nashik")
    db.add(listing)
    db.commit()

    offer = Offer(listing_id=listing.id, buyer_id=user.id, offered_price=1900, quantity=10, status=OfferStatus.CONFIRMED.value)
    db.add(offer)
    db.commit()

    with pytest.MonkeyPatch.context() as m:
        m.setattr(settings, "RAZORPAY_KEY_ID", "")
        m.setattr(settings, "RAZORPAY_KEY_SECRET", "")

        order_res = client.post("/marketplace/payments/create-order", headers={"Authorization": f"Bearer {token}"}, json={"offer_id": offer.id})
        assert order_res.status_code == 201
        data = order_res.json()
        assert data["is_test_mode"] is True
        assert "DEMO ORDER" in data["notice"]
        order_id = data["payment_order_id"]

        # Try to mark paid -> must be blocked
        verify_res = client.post("/marketplace/payments/verify", json={
            "order_id": order_id,
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": "pay_fake",
            "razorpay_signature": "sig_fake"
        })
        assert verify_res.status_code == 400
        assert "Demo orders created without Razorpay credentials cannot be marked paid" in verify_res.json()["detail"]


# ──────────────────────────────────────────────
# 4. Sensor Endpoint: Valid Device Key Required, Rejects Unregistered, Validates Ranges
# ──────────────────────────────────────────────
def test_sensor_endpoint_strict_authentication_and_range_validation(client, db):
    user, token = create_test_user(db, "9870000004")
    farm = Farm(user_id=user.id, name="Sensor Farm", village="Satara", size_acres=4)
    db.add(farm)
    db.commit()

    device_id = f"ESP32_SEC_{int(datetime.now(timezone.utc).timestamp())}"

    # 1. Register device
    reg_res = client.post(
        "/sensors/devices/register",
        headers={"Authorization": f"Bearer {token}"},
        json={"farm_id": farm.id, "device_name": "ESP32 Field 1", "device_identifier": device_id}
    )
    assert reg_res.status_code == 201
    valid_key = reg_res.json()["api_key"]

    # 2. Reject missing X-Device-Key header
    res_no_key = client.post("/sensors/readings", json={"sensor_id": device_id, "moisture": 35.0})
    assert res_no_key.status_code == 401
    assert "X-Device-Key header is required" in res_no_key.json()["detail"]

    # 3. Reject unregistered device
    res_unregistered = client.post("/sensors/readings", headers={"X-Device-Key": valid_key}, json={"sensor_id": "UNKNOWN_NODE_999", "moisture": 35.0})
    assert res_unregistered.status_code == 401
    assert "Device is not registered" in res_unregistered.json()["detail"]

    # 4. Reject wrong device key
    res_wrong_key = client.post("/sensors/readings", headers={"X-Device-Key": "wrong_key_123"}, json={"sensor_id": device_id, "moisture": 35.0})
    assert res_wrong_key.status_code == 401
    assert "Invalid device key" in res_wrong_key.json()["detail"]

    # 5. Out of physical range validation (Pydantic validator: moisture must be <= 100)
    res_range_error = client.post("/sensors/readings", headers={"X-Device-Key": valid_key}, json={"sensor_id": device_id, "moisture": 150.0})
    assert res_range_error.status_code == 422

    # 6. Valid ingestion
    res_valid = client.post("/sensors/readings", headers={"X-Device-Key": valid_key}, json={"sensor_id": device_id, "moisture": 45.0, "ph": 7.2})
    assert res_valid.status_code == 201
    assert res_valid.json()["status"] == "success"


# ──────────────────────────────────────────────
# 5. Offers & Transport Security (Seller Accepts, Buyer cannot Confirm, Transporters only)
# ──────────────────────────────────────────────
def test_offers_and_transport_permission_rules(client, db):
    seller, seller_token = create_test_user(db, "9870000005", role=UserRole.FARMER.value)
    buyer, buyer_token = create_test_user(db, "9870000006", role=UserRole.BUYER.value)
    transporter, transporter_token = create_test_user(db, "9870000007", role=UserRole.TRANSPORTER.value)

    listing = Listing(farmer_id=seller.id, crop="Wheat", quantity_quintals=20, expected_price=2800, location="Baramati")
    db.add(listing)
    db.commit()

    # Buyer places offer
    offer_res = client.post(
        f"/marketplace/listings/{listing.id}/offer",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"offered_price": 2750, "quantity": 10}
    )
    assert offer_res.status_code == 201
    offer_id = offer_res.json()["id"]

    # Buyer attempts to confirm their own offer -> MUST BE BLOCKED
    buyer_confirm = client.put(
        f"/marketplace/offers/{offer_id}/status",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"status": OfferStatus.CONFIRMED.value}
    )
    assert buyer_confirm.status_code == 403
    assert "Only the seller" in buyer_confirm.json()["detail"]

    # Seller confirms offer -> ALLOWED
    seller_confirm = client.put(
        f"/marketplace/offers/{offer_id}/status",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={"status": OfferStatus.CONFIRMED.value}
    )
    assert seller_confirm.status_code == 200
    assert seller_confirm.json()["status"] == OfferStatus.CONFIRMED.value

    # Transport request by seller
    t_req = client.post(
        "/marketplace/transport/request",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={"pickup_location": "Baramati Farm", "drop_location": "Pune APMC", "weight_quintals": 10, "preferred_date": "2026-11-20"}
    )
    assert t_req.status_code == 201
    transport_id = t_req.json()["id"]

    # Buyer (non-transporter) attempts to accept job -> MUST BE BLOCKED
    buyer_accept = client.put(
        f"/marketplace/transport/{transport_id}/status",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"status": TransportStatus.ACCEPTED.value}
    )
    assert buyer_accept.status_code == 403
    assert "Only certified transporters" in buyer_accept.json()["detail"]

    # Certified transporter accepts job -> ALLOWED
    trans_accept = client.put(
        f"/marketplace/transport/{transport_id}/status",
        headers={"Authorization": f"Bearer {transporter_token}"},
        json={"status": TransportStatus.ACCEPTED.value}
    )
    assert trans_accept.status_code == 200
    assert trans_accept.json()["status"] == TransportStatus.ACCEPTED.value


# ──────────────────────────────────────────────
# 6. JWT_SECRET and OTP_PEPPER >= 64 Chars & HMAC-SHA256 OTP Hash
# ──────────────────────────────────────────────
def test_secrets_minimum_length_and_otp_hmac():
    assert len(settings.JWT_SECRET) >= 64
    assert len(settings.OTP_PEPPER) >= 64

    # Verify HMAC hashing uses pepper
    hashed = hash_otp_hmac("9876543210", "123456")
    expected = hmac.new(settings.OTP_PEPPER.encode("utf-8"), b"9876543210:123456", hashlib.sha256).hexdigest()
    assert hmac.compare_digest(hashed, expected)


# ──────────────────────────────────────────────
# 7. Users Cannot Escalate to Admin or Transporter
# ──────────────────────────────────────────────
def test_users_cannot_escalate_roles(client, db):
    user, token = create_test_user(db, "9870000008", role=UserRole.FARMER.value)

    # Attempt to escalate to admin
    res_admin_esc = client.put("/profile", headers={"Authorization": f"Bearer {token}"}, json={"role": "admin"})
    assert res_admin_esc.status_code == 403
    assert "cannot self-assign" in res_admin_esc.json()["detail"]

    # Attempt to escalate to transporter
    res_trans_esc = client.put("/profile", headers={"Authorization": f"Bearer {token}"}, json={"role": "transporter"})
    assert res_trans_esc.status_code == 403
    assert "cannot self-assign" in res_trans_esc.json()["detail"]

    # Transition to buyer is allowed
    res_buyer = client.put("/profile", headers={"Authorization": f"Bearer {token}"}, json={"role": "buyer"})
    assert res_buyer.status_code == 200
    assert res_buyer.json()["role"] == "buyer"


# ──────────────────────────────────────────────
# 8. Password-Based Signup and Login
# ──────────────────────────────────────────────
def test_password_signup_and_login_flow(client):
    # 1. Signup a new user
    signup_res = client.post(
        "/auth/signup",
        json={"phone": "9876500001", "password": "securepassword123", "name": "Professor Demo"}
    )
    assert signup_res.status_code == 201
    signup_data = signup_res.json()
    assert "access_token" in signup_data
    assert signup_data["token_type"] == "bearer"
    assert signup_data["user"]["phone"] == "+919876500001"
    assert signup_data["user"]["name"] == "Professor Demo"

    token = signup_data["access_token"]

    # Verify token can access protected endpoints like /profile
    prof_res = client.get("/profile", headers={"Authorization": f"Bearer {token}"})
    assert prof_res.status_code == 200
    assert prof_res.json()["phone"] == "+919876500001"

    # 2. Login with valid credentials
    login_res = client.post(
        "/auth/login",
        json={"phone": "9876500001", "password": "securepassword123"}
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # 3. Login with wrong password -> 401
    bad_login = client.post(
        "/auth/login",
        json={"phone": "9876500001", "password": "wrongpassword"}
    )
    assert bad_login.status_code == 401
    assert "Invalid phone number or password" in bad_login.json()["detail"]

    # 4. Login with non-existent phone -> 401
    unreg_login = client.post(
        "/auth/login",
        json={"phone": "9876500999", "password": "securepassword123"}
    )
    assert unreg_login.status_code == 401

    # 5. Duplicate signup on already registered phone -> 400
    dup_signup = client.post(
        "/auth/signup",
        json={"phone": "9876500001", "password": "anotherpassword"}
    )
    assert dup_signup.status_code == 400
    assert "already registered" in dup_signup.json()["detail"]

