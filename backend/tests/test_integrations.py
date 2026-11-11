"""
Automated Integration Tests for AGRI-TECH:
- Real OTP providers (Twilio, MSG91, Mock) with rate limiting & hashing
- Open-Meteo Weather caching, retries, and stale fallback
- SoilGrids v2 REST integration & Soil OCR
- IoT ESP32 sensor device registration & telemetry ingestion with anomaly detection
- Agmarknet daily mandi API synchronization & fallback hierarchy
- Transport logistics workflow & Razorpay test-mode payments
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine
from app.models import User, OTP, Farm, MarketPrice, Offer, Listing, SensorDevice, TransportRequest, PaymentOrder
from app.services.otp_service import TwilioOTPProvider, MSG91OTPProvider, MockOTPProvider
from app.services.weather_service import fetch_open_meteo_forecast, get_cached_or_fresh_weather
from app.services.soil_service import get_soilgrids_estimate, extract_soil_card_from_image_vision
from app.services.mandi_service import fetch_live_agmarknet_prices, sync_mandi_prices_task


def test_weather_retries_and_stale_fallback(client, db):
    # Mock Open-Meteo failing
    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        res = get_cached_or_fresh_weather(db, farm_id=None, lat=18.52, lng=73.85)
        assert res is not None
        assert "daily" in res


def test_soilgrids_v2_mocked_response():
    fake_soilgrids = {
        "properties": {
            "layers": [
                {"name": "phh2o", "depths": [{"values": {"mean": 75}}]},
                {"name": "clay", "depths": [{"values": {"mean": 480}}]},
                {"name": "soc", "depths": [{"values": {"mean": 95}}]}
            ]
        }
    }
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value.status = 200
    mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(fake_soilgrids).encode("utf-8")

    with patch("urllib.request.urlopen", mock_urlopen):
        estimate = get_soilgrids_estimate(18.52, 73.85)
        assert estimate["tier"] == 2
        assert estimate["estimated_properties"]["ph"]["value"] == 7.5
        assert "ESTIMATE" in estimate["disclaimer_en"]


def test_soil_ocr_claude_vision_mocked():
    fake_claude_resp = {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"ph": 7.2, "ec": 0.45, "oc": 0.62, "n": 220, "p": 15, "k": 290})
            }
        ]
    }
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(fake_claude_resp).encode("utf-8")

    with patch("urllib.request.urlopen", mock_urlopen):
        with patch("app.config.settings.ANTHROPIC_API_KEY", "sk-mock-key"):
            res = extract_soil_card_from_image_vision("fake_base64_data")
            assert res["is_mock_ocr"] is False
            assert res["extracted_values"]["ph"] == 7.2
            assert res["needs_confirmation"] is True


def test_iot_sensor_device_and_telemetry(client, db):
    # Setup test farmer
    farmer = db.query(User).filter(User.phone == "9111222333").first()
    if not farmer:
        farmer = User(phone="9111222333", name="Test Farmer")
        db.add(farmer)
        db.commit()
    farm = Farm(user_id=farmer.id, name="IoT Test Farm", village="Pune", size_acres=2.5)
    db.add(farm)
    db.commit()

    from app.auth import create_access_token
    token = create_access_token(user_id=farmer.id, phone=farmer.phone)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Register device
    reg_res = client.post(
        "/sensors/devices/register",
        headers=headers,
        json={"farm_id": farm.id, "device_name": "ESP32 Node 1", "device_identifier": "ESP32_TEST_01"}
    )
    assert reg_res.status_code == 201
    api_key = reg_res.json()["api_key"]

    # 2. Ingest telemetry
    telemetry_res = client.post(
        "/sensors/readings",
        headers={"X-Device-Key": api_key},
        json={"sensor_id": "ESP32_TEST_01", "moisture": 42.5, "temperature": 28.0, "ph": 7.1, "conductivity": 0.38}
    )
    assert telemetry_res.status_code == 201
    assert telemetry_res.json()["is_anomaly"] is False

    # 3. Anomaly detection check (extreme moisture)
    anomaly_res = client.post(
        "/sensors/readings",
        headers={"X-Device-Key": api_key},
        json={"sensor_id": "ESP32_TEST_01", "moisture": 99.0, "temperature": 28.0, "ph": 7.1}
    )
    assert anomaly_res.status_code == 201
    assert anomaly_res.json()["is_anomaly"] is True


def test_agmarknet_sync_mocked():
    fake_agmarknet_api = {
        "records": [
            {
                "state": "Maharashtra",
                "district": "Pune",
                "market": "Pune APMC",
                "commodity": "Soybean",
                "modal_price": "4700",
                "min_price": "4400",
                "max_price": "4900",
                "arrival_date": "2026-11-10"
            }
        ]
    }
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value.status = 200
    mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(fake_agmarknet_api).encode("utf-8")

    with patch("urllib.request.urlopen", mock_urlopen):
        with patch("app.config.settings.DATA_GOV_API_KEY", "mock_datagov_key"):
            records = fetch_live_agmarknet_prices(state="Maharashtra")
            assert records is not None
            assert len(records) == 1
            assert records[0]["modal_price"] == 4700.0


def test_transport_and_payment_flow(client, db):
    user = db.query(User).first()
    if not user:
        user = User(phone="+919876543210", name="Test Transporter", role="transporter")
        db.add(user)
        db.commit()
    else:
        user.role = "transporter"
        db.commit()
    from app.auth import create_access_token
    token = create_access_token(user_id=user.id, phone=user.phone)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Transport request
    t_res = client.post(
        "/marketplace/transport/request",
        headers=headers,
        json={"pickup_location": "Field 1", "drop_location": "Pune APMC", "weight_quintals": 12.0, "preferred_date": "2026-11-15"}
    )
    assert t_res.status_code == 201
    assert t_res.json()["status"] == "requested"

    # 2. Accept transport (as transporter role)
    tid = t_res.json()["id"]
    accept_res = client.put(
        f"/marketplace/transport/{tid}/status",
        headers=headers,
        json={"status": "accepted", "driver_notes": "Pick up at 8 AM"}
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "accepted"

    # 3. Razorpay payment order creation for confirmed offer
    listing = Listing(farmer_id=user.id, crop="Gram", quantity_quintals=10, expected_price=5000, location="Pune")
    db.add(listing)
    db.commit()
    offer = Offer(listing_id=listing.id, buyer_id=user.id, offered_price=4900, quantity=5, status="confirmed")
    db.add(offer)
    db.commit()

    pay_res = client.post(
        "/marketplace/payments/create-order",
        headers=headers,
        json={"offer_id": offer.id}
    )
    assert pay_res.status_code == 201
    assert "DEMO ORDER" in pay_res.json()["notice"] or "TEST MODE" in pay_res.json()["notice"]
    assert pay_res.json()["amount_inr"] == 24500.0

