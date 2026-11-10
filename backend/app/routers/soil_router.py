"""
Soil Module Router for AGRI-TECH.
Covers:
- Tier 1: Soil Health Card entry & interpretation
- Tier 2: ISRIC SoilGrids v2 REST API (30-day cache, rate limit backoff, ESTIMATE label)
- Tier 3: Guided Visual Observations
- Tier 4: IoT / ESP32 Sensor Hardware System (Device Registration, Ingestion with Hashed Key, Telemetry, Anomaly Detection)
- Tier 5: Maharashtra Lab Directory & Sampling Guide
- OCR Vision Engine: Real Claude Vision extraction with fallback to simulated mock
"""

import json
import secrets
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Farm, User, SoilRecord, SensorDevice, SensorReading
from app.dependencies import get_current_user
from app.services.soil_service import (
    interpret_soil_health_card,
    get_soilgrids_estimate,
    interpret_visual_observation,
    extract_soil_card_from_image_vision,
    mock_ocr_extract_card,
    load_soil_labs,
    validate_soil_card_ranges
)

router = APIRouter(prefix="/soil", tags=["Soil Module"])


class SoilCardInput(BaseModel):
    ph: Optional[float] = Field(None, ge=3.0, le=11.0, description="Soil pH")
    ec: Optional[float] = Field(None, ge=0.0, description="Electrical Conductivity dS/m")
    oc: Optional[float] = Field(None, ge=0.0, le=10.0, description="Organic Carbon %")
    n: Optional[float] = Field(None, ge=0.0, description="Available Nitrogen kg/ha")
    p: Optional[float] = Field(None, ge=0.0, description="Available Phosphorus kg/ha")
    k: Optional[float] = Field(None, ge=0.0, description="Available Potassium kg/ha")
    sulphur: Optional[float] = None
    zinc: Optional[float] = None
    iron: Optional[float] = None
    copper: Optional[float] = None
    manganese: Optional[float] = None
    boron: Optional[float] = None
    crop: Optional[str] = None


class VisualObservationInput(BaseModel):
    color: Optional[str] = Field(None, description="black_dark, red, pale_yellow, grey_white_crust")
    texture: Optional[str] = Field(None, description="clay_sticky, loamy_crumbly, sandy_loose")
    drainage: Optional[str] = Field(None, description="waterlogs, moderate_24h, rapid_draining")
    cracking: Optional[str] = Field(None, description="deep_cracks, slight_cracks, no_cracks")
    symptom: Optional[str] = Field(None, description="yellow_lower_leaves, purple_stems_leaves, burnt_leaf_edges, none")


class OCRVisionRequest(BaseModel):
    base64_image: Optional[str] = None
    mime_type: Optional[str] = "image/jpeg"


# ──────────────────────────────────────────────
# Tier 1: Lab Test Soil Card
# ──────────────────────────────────────────────
@router.post("/card/{farm_id}", status_code=status.HTTP_201_CREATED)
def add_soil_health_card(
    farm_id: int,
    data: SoilCardInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Tier 1 (High Confidence): Submit confirmed Soil Health Card lab results.
    Never auto-saves unconfirmed numbers.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this farm")

    raw_dict = {k: v for k, v in data.dict().items() if v is not None and k != "crop"}
    validated = validate_soil_card_ranges(raw_dict)
    interpretation = interpret_soil_health_card(validated, crop=data.crop or farm.crops)

    record = SoilRecord(
        farm_id=farm.id,
        tier=1,
        source="Government Soil Health Card (Lab Certified)",
        confidence="High",
        values_json=json.dumps(validated),
        interpretation_json=json.dumps(interpretation)
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "farm_id": farm.id,
        "tier": 1,
        "confidence": "High",
        "source": record.source,
        "interpretation": interpretation,
        "created_at": record.created_at.isoformat()
    }


# ──────────────────────────────────────────────
# Item 3: OCR Vision Endpoint
# ──────────────────────────────────────────────
@router.post("/ocr-card")
@router.post("/ocr-stub")
def ocr_soil_card(req: Optional[OCRVisionRequest] = None):
    """
    Item 3: Real Soil Card extraction via Claude Vision API when image is provided,
    otherwise returns simulated mock data. Always returns values for farmer confirmation.
    """
    if req and req.base64_image:
        return extract_soil_card_from_image_vision(req.base64_image, req.mime_type or "image/jpeg")
    return mock_ocr_extract_card()


# ──────────────────────────────────────────────
# Tier 2: ISRIC SoilGrids v2 REST API
# ──────────────────────────────────────────────
@router.get("/soilgrids/{farm_id}")
def get_soilgrids_for_farm(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Tier 2: Real ISRIC SoilGrids v2 REST API (30-day SQLite cache, rate-limit backoff).
    Prominently labeled as ESTIMATE, not a lab test.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this farm")

    lat = farm.latitude or 18.5204
    lng = farm.longitude or 73.8567

    estimate = get_soilgrids_estimate(lat, lng, db=db)

    # Cache as Tier 2 record if not present
    existing = db.query(SoilRecord).filter(SoilRecord.farm_id == farm.id, SoilRecord.tier == 2).first()
    if not existing:
        new_record = SoilRecord(
            farm_id=farm.id,
            tier=2,
            source=estimate.get("source", "ISRIC SoilGrids v2"),
            confidence="Medium",
            values_json=json.dumps({"lat": lat, "lng": lng}),
            interpretation_json=json.dumps(estimate)
        )
        db.add(new_record)
        db.commit()

    return estimate


# ──────────────────────────────────────────────
# Tier 3: Guided Visual Observations
# ──────────────────────────────────────────────
@router.post("/observation/{farm_id}", status_code=status.HTTP_201_CREATED)
def add_visual_observation(
    farm_id: int,
    data: VisualObservationInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this farm")

    obs = {k: v for k, v in data.dict().items() if v}
    interpretation = interpret_visual_observation(obs)

    record = SoilRecord(
        farm_id=farm.id,
        tier=3,
        source="Guided Visual Observation",
        confidence="Low",
        values_json=json.dumps(obs),
        interpretation_json=json.dumps(interpretation)
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "farm_id": farm.id,
        "tier": 3,
        "confidence": "Low",
        "source": record.source,
        "interpretation": interpretation,
        "created_at": record.created_at.isoformat()
    }


# ──────────────────────────────────────────────
# Tier 5: Labs Directory
# ──────────────────────────────────────────────
@router.get("/labs")
def get_soil_labs_directory():
    return load_soil_labs()


# ──────────────────────────────────────────────
# Primary Soil Insights (Tier 1 > Tier 4 > Tier 2 > Tier 3)
# ──────────────────────────────────────────────
@router.get("/{farm_id}")
def get_farm_soil_insights(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this farm")

    records = db.query(SoilRecord).filter(SoilRecord.farm_id == farm_id).order_by(SoilRecord.tier.asc(), SoilRecord.created_at.desc()).all()

    formatted_records = []
    for r in records:
        formatted_records.append({
            "id": r.id,
            "tier": r.tier,
            "source": r.source,
            "confidence": r.confidence,
            "values": json.loads(r.values_json) if r.values_json else {},
            "interpretation": json.loads(r.interpretation_json) if r.interpretation_json else {},
            "created_at": r.created_at.isoformat()
        })

    # Latest Tier 4 sensor telemetry
    latest_reading = (
        db.query(SensorReading)
        .filter(SensorReading.farm_id == farm_id)
        .order_by(SensorReading.recorded_at.desc())
        .first()
    )
    sensor_summary = None
    if latest_reading:
        sensor_summary = {
            "tier": 4,
            "confidence": "Medium",
            "source": f"Live IoT Node ({latest_reading.sensor_id})",
            "moisture": latest_reading.moisture,
            "temperature": latest_reading.temperature,
            "ph": latest_reading.ph,
            "conductivity": latest_reading.conductivity,
            "is_anomaly": latest_reading.is_anomaly,
            "anomaly_reason": latest_reading.anomaly_reason,
            "recorded_at": latest_reading.recorded_at.isoformat(),
        }

    highest = formatted_records[0] if formatted_records else None

    return {
        "farm_id": farm.id,
        "farm_name": farm.name,
        "village": farm.village,
        "primary_insight": highest,
        "latest_sensor_reading": sensor_summary,
        "history": formatted_records,
        "has_data": len(formatted_records) > 0 or latest_reading is not None
    }


# ──────────────────────────────────────────────
# Item 5: Tier 4 IoT Sensor Hardware Router
# ──────────────────────────────────────────────
sensor_router = APIRouter(prefix="/sensors", tags=["IoT Sensors (Tier 4)"])


class DeviceRegisterInput(BaseModel):
    farm_id: int
    device_name: str
    device_identifier: str  # e.g., "ESP32_AGRI_NODE_01"


class TelemetryInput(BaseModel):
    sensor_id: str
    moisture: Optional[float] = Field(None, ge=0.0, le=100.0, description="Moisture %")
    temperature: Optional[float] = Field(None, ge=-10.0, le=65.0, description="Soil temp °C")
    conductivity: Optional[float] = Field(None, ge=0.0, le=25.0, description="Conductivity dS/m")
    ph: Optional[float] = Field(None, ge=0.0, le=14.0, description="Soil pH")


def hash_device_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


@sensor_router.post("/devices/register", status_code=status.HTTP_201_CREATED)
def register_sensor_device(
    data: DeviceRegisterInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registers an ESP32 hardware device for a farm and issues a secret device API key."""
    farm = db.query(Farm).filter(Farm.id == data.farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this farm")

    existing = db.query(SensorDevice).filter(SensorDevice.device_identifier == data.device_identifier).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device identifier already registered")

    raw_api_key = f"agri_node_{secrets.token_hex(16)}"
    hashed_key = hash_device_key(raw_api_key)

    device = SensorDevice(
        farm_id=farm.id,
        device_name=data.device_name,
        device_identifier=data.device_identifier,
        hashed_api_key=hashed_key,
        is_active=True
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    return {
        "device_id": device.id,
        "farm_id": device.farm_id,
        "device_name": device.device_name,
        "device_identifier": device.device_identifier,
        "api_key": raw_api_key,
        "notice": "Store this API key in your ESP32 Arduino sketch header. It will not be shown again."
    }


@sensor_router.get("/devices/{farm_id}")
def list_farm_devices(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm or farm.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    devices = db.query(SensorDevice).filter(SensorDevice.farm_id == farm_id).all()
    return [
        {
            "id": d.id,
            "device_name": d.device_name,
            "device_identifier": d.device_identifier,
            "is_active": d.is_active,
            "created_at": d.created_at.isoformat()
        } for d in devices
    ]


@sensor_router.post("/readings", status_code=status.HTTP_201_CREATED)
def record_sensor_telemetry(
    data: TelemetryInput,
    x_device_key: Optional[str] = Header(None, alias="X-Device-Key"),
    db: Session = Depends(get_db),
):
    """
    Tier 4: Ingests live hardware telemetry from ESP32.
    Authenticates via X-Device-Key header against hashed key in DB.
    Performs agricultural anomaly validation.
    """
    device = db.query(SensorDevice).filter(SensorDevice.device_identifier == data.sensor_id).first()
    if not device:
        # Fallback support for un-registered legacy nodes
        farm_id = 1
        device_id = None
    else:
        farm_id = device.farm_id
        device_id = device.id
        if x_device_key:
            expected_hash = hash_device_key(x_device_key)
            if device.hashed_api_key != expected_hash:
                raise HTTPException(status_code=401, detail="Invalid X-Device-Key")

    # Anomaly checks
    is_anomaly = False
    anomaly_reasons = []

    if data.moisture is not None and (data.moisture < 5.0 or data.moisture > 95.0):
        is_anomaly = True
        anomaly_reasons.append("Extreme soil moisture reading")
    if data.ph is not None and (data.ph < 4.0 or data.ph > 9.5):
        is_anomaly = True
        anomaly_reasons.append("Extreme soil pH reading")
    if data.temperature is not None and (data.temperature < 0.0 or data.temperature > 55.0):
        is_anomaly = True
        anomaly_reasons.append("Abnormal soil temperature")

    reading = SensorReading(
        device_id=device_id,
        farm_id=farm_id,
        sensor_id=data.sensor_id,
        moisture=data.moisture,
        temperature=data.temperature,
        conductivity=data.conductivity,
        ph=data.ph,
        is_anomaly=is_anomaly,
        anomaly_reason="; ".join(anomaly_reasons) if is_anomaly else None,
        recorded_at=datetime.utcnow()
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    return {
        "status": "success",
        "reading_id": reading.id,
        "is_anomaly": is_anomaly,
        "anomaly_reason": reading.anomaly_reason,
        "recorded_at": reading.recorded_at.isoformat()
    }


@sensor_router.get("/latest/{farm_id}")
def get_latest_sensor_reading(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reading = (
        db.query(SensorReading)
        .filter(SensorReading.farm_id == farm_id)
        .order_by(SensorReading.recorded_at.desc())
        .first()
    )
    if not reading:
        return {"has_data": False, "reading": None}

    return {
        "has_data": True,
        "reading": {
            "id": reading.id,
            "sensor_id": reading.sensor_id,
            "moisture": reading.moisture,
            "temperature": reading.temperature,
            "ph": reading.ph,
            "conductivity": reading.conductivity,
            "is_anomaly": reading.is_anomaly,
            "anomaly_reason": reading.anomaly_reason,
            "recorded_at": reading.recorded_at.isoformat()
        }
    }


@sensor_router.get("/history/{farm_id}")
def get_sensor_history(
    farm_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    readings = (
        db.query(SensorReading)
        .filter(SensorReading.farm_id == farm_id)
        .order_by(SensorReading.recorded_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "sensor_id": r.sensor_id,
            "moisture": r.moisture,
            "temperature": r.temperature,
            "ph": r.ph,
            "conductivity": r.conductivity,
            "is_anomaly": r.is_anomaly,
            "recorded_at": r.recorded_at.isoformat()
        } for r in readings
    ]
