"""
SQLAlchemy ORM models for AGRI-TECH.
Defines the database schema for PostgreSQL and SQLite.
Enforces standard Python Enums for Offer and Transport statuses.
Uses timezone-aware UTC datetime defaults.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    """Helper returning timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class OfferStatus(str, enum.Enum):
    OFFER_MADE = "offer_made"
    CONFIRMED = "confirmed"
    DELIVERED = "delivered"
    REJECTED = "rejected"


class TransportStatus(str, enum.Enum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    CREATED = "created"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class UserRole(str, enum.Enum):
    FARMER = "farmer"
    BUYER = "buyer"
    TRANSPORTER = "transporter"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=True)
    language_preference = Column(String(10), default="mr")
    role = Column(String(30), default=UserRole.FARMER.value, index=True)
    is_verified = Column(Boolean, default=False)
    rating = Column(Float, default=5.0)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    farms = relationship("Farm", back_populates="owner", cascade="all, delete-orphan")


class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(50), nullable=False, index=True)
    otp_code = Column(String(128), nullable=False)  # HMAC-SHA256 hex digest
    created_at = Column(DateTime(timezone=True), default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)


class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    village = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    size_acres = Column(Float, nullable=False)
    crops = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    owner = relationship("User", back_populates="farms")
    sensors = relationship("SensorDevice", back_populates="farm", cascade="all, delete-orphan")


class WeatherCache(Base):
    __tablename__ = "weather_cache"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    forecast_data = Column(Text, nullable=False)
    cached_at = Column(DateTime(timezone=True), default=utc_now, index=True)


class SoilRecord(Base):
    __tablename__ = "soil_records"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    tier = Column(Integer, nullable=False)
    source = Column(String(200), nullable=False)
    confidence = Column(String(50), nullable=False)
    values_json = Column(Text, nullable=False)
    interpretation_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)


class SensorDevice(Base):
    __tablename__ = "sensor_devices"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    device_name = Column(String(200), nullable=False)
    device_identifier = Column(String(100), unique=True, index=True, nullable=False)
    hashed_api_key = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    farm = relationship("Farm", back_populates="sensors")
    readings = relationship("SensorReading", back_populates="device", cascade="all, delete-orphan")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("sensor_devices.id"), nullable=False, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    sensor_id = Column(String(100), nullable=False)
    moisture = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    conductivity = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    is_anomaly = Column(Boolean, default=False)
    anomaly_reason = Column(String(300), nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    device = relationship("SensorDevice", back_populates="readings")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), default="Farming Query")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    sender = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True)
    is_flagged = Column(Boolean, default=False, index=True)
    flag_reason = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    session = relationship("ChatSession", back_populates="messages")


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String(200), nullable=False, index=True)
    mandi_name = Column(String(200), nullable=False, index=True)
    district = Column(String(100), nullable=False)
    min_price = Column(Float, nullable=False)
    max_price = Column(Float, nullable=False)
    modal_price = Column(Float, nullable=False)
    unit = Column(String(50), default="Rs/quintal")
    arrival_date = Column(String(50), nullable=False)
    source = Column(String(50), default="live")
    is_mock = Column(Boolean, default=False)


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    crop = Column(String(200), nullable=False, index=True)
    quantity_quintals = Column(Float, nullable=False)
    quality_grade = Column(String(50), default="Grade A")
    expected_price = Column(Float, nullable=False)
    location = Column(String(200), nullable=False)
    photos_json = Column(Text, nullable=True)
    status = Column(String(50), default="active", index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    farmer = relationship("User")
    offers = relationship("Offer", back_populates="listing", cascade="all, delete-orphan")


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    offered_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    status = Column(String(50), default=OfferStatus.OFFER_MADE.value, index=True)
    buyer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    listing = relationship("Listing", back_populates="offers")
    buyer = relationship("User")
    payment_orders = relationship("PaymentOrder", back_populates="offer", cascade="all, delete-orphan")


class TransportRequest(Base):
    __tablename__ = "transport_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    transporter_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=True, index=True)
    pickup_location = Column(String(250), nullable=False)
    drop_location = Column(String(250), nullable=False)
    weight_quintals = Column(Float, nullable=False)
    preferred_date = Column(String(50), nullable=False)
    status = Column(String(50), default=TransportStatus.REQUESTED.value, index=True)
    driver_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    requester = relationship("User", foreign_keys=[user_id])
    transporter = relationship("User", foreign_keys=[transporter_id])


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    razorpay_order_id = Column(String(100), unique=True, index=True, nullable=False)
    razorpay_payment_id = Column(String(100), nullable=True)
    amount_inr = Column(Float, nullable=False)
    status = Column(String(50), default=PaymentStatus.CREATED.value, index=True)
    is_test_mode = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    offer = relationship("Offer", back_populates="payment_orders")
    buyer = relationship("User")
