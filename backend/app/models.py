"""
SQLAlchemy ORM models for AGRI-TECH.
Defines the database schema for Users, OTPs, Farms, Soil, Weather, Chat, Marketplace, Sensors, Transport, and Payments.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """
    User model — represents a farmer, buyer, transporter, or admin.
    Identified by phone number (primary auth mechanism in rural India).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)  # Indian mobile number
    name = Column(String, nullable=True)  # Farmer's name, set during profile completion
    language_preference = Column(String, default="mr")  # Default: Marathi ("mr")
    role = Column(String, default="farmer", index=True)  # "farmer", "buyer", "transporter", "admin"
    is_verified = Column(Boolean, default=False)  # Verified buyer or farmer badge
    rating = Column(Float, default=5.0)  # User rating (1.0 to 5.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farms = relationship("Farm", back_populates="owner", cascade="all, delete-orphan")


class OTP(Base):
    """
    OTP model — temporary one-time password storage for phone-based auth.
    Supports hashed storage, attempt counting, and expiration.
    """
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False, index=True)
    otp_code = Column(String, nullable=False)  # Hashed or plain (sha256 hex)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)  # Max 5 verify attempts allowed


class Farm(Base):
    """
    Farm model — represents a farmer's agricultural plot.
    """
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    village = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    size_acres = Column(Float, nullable=False)
    crops = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="farms")
    sensors = relationship("SensorDevice", back_populates="farm", cascade="all, delete-orphan")


class WeatherCache(Base):
    """
    Weather cache model to store forecasts for slow internet connections.
    """
    __tablename__ = "weather_cache"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    forecast_data = Column(Text, nullable=False)  # JSON-encoded forecast
    cached_at = Column(DateTime, default=datetime.utcnow, index=True)


class SoilRecord(Base):
    """
    Tiered soil insight records.
    Tier 1 = Lab Test Card (High confidence)
    Tier 2 = ISRIC SoilGrids Estimate (Medium-Low confidence)
    Tier 3 = Farmer Visual Observation (Low confidence)
    """
    __tablename__ = "soil_records"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    tier = Column(Integer, nullable=False)  # 1, 2, or 3
    source = Column(String, nullable=False)
    confidence = Column(String, nullable=False)  # "High", "Medium", "Low"
    values_json = Column(Text, nullable=False)
    interpretation_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class SensorDevice(Base):
    """
    Tier 4: Registered IoT / ESP32 hardware device assigned to a farm.
    Authenticates telemetry postings using a hashed API key.
    """
    __tablename__ = "sensor_devices"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    device_name = Column(String, nullable=False)  # e.g., "Field 1 Moisture & pH Node"
    device_identifier = Column(String, unique=True, index=True, nullable=False)  # e.g., "ESP32_AGRI_01"
    hashed_api_key = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    farm = relationship("Farm", back_populates="sensors")
    readings = relationship("SensorReading", back_populates="device", cascade="all, delete-orphan")


class SensorReading(Base):
    """
    Tier 4: Live hardware telemetry readings from ESP32 / LoRaWAN nodes.
    Includes anomaly flags for out-of-range agricultural measurements.
    """
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("sensor_devices.id"), nullable=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    sensor_id = Column(String, nullable=False)  # Device identifier string
    moisture = Column(Float, nullable=True)  # Soil moisture % (0 - 100)
    temperature = Column(Float, nullable=True)  # Soil temp °C (-10 - 60)
    conductivity = Column(Float, nullable=True)  # EC dS/m (0 - 20)
    ph = Column(Float, nullable=True)  # Soil pH (0 - 14)
    is_anomaly = Column(Boolean, default=False)
    anomaly_reason = Column(String, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    device = relationship("SensorDevice", back_populates="readings")


class ChatSession(Base):
    """
    User conversation session with the multilingual AI agricultural chatbot.
    """
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, default="Farming Query")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """
    Individual message in a chat session.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    sender = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True)
    is_flagged = Column(Boolean, default=False, index=True)
    flag_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class MarketPrice(Base):
    """
    Reference Mandi APMC prices (data.gov.in Agmarknet API sync + static fallback).
    """
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String, nullable=False, index=True)
    mandi_name = Column(String, nullable=False, index=True)
    district = Column(String, nullable=False)
    min_price = Column(Float, nullable=False)
    max_price = Column(Float, nullable=False)
    modal_price = Column(Float, nullable=False)
    unit = Column(String, default="Rs/quintal")
    arrival_date = Column(String, nullable=False)
    source = Column(String, default="live")  # "live", "cached", "mock"
    is_mock = Column(Boolean, default=False)


class Listing(Base):
    """
    Direct farmer-to-buyer crop listings.
    """
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    crop = Column(String, nullable=False, index=True)
    quantity_quintals = Column(Float, nullable=False)
    quality_grade = Column(String, default="Grade A")
    expected_price = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    photos_json = Column(Text, nullable=True)
    status = Column(String, default="active", index=True)  # "active", "sold", "cancelled"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farmer = relationship("User")
    offers = relationship("Offer", back_populates="listing", cascade="all, delete-orphan")


class Offer(Base):
    """
    Buyer offers on farmer crop listings.
    Flow: listed -> offer_made -> confirmed -> delivered.
    """
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    offered_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    status = Column(String, default="offer_made", index=True)  # "offer_made", "confirmed", "delivered", "rejected"
    buyer_notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    listing = relationship("Listing", back_populates="offers")
    buyer = relationship("User")
    payment_orders = relationship("PaymentOrder", back_populates="offer", cascade="all, delete-orphan")


class TransportRequest(Base):
    """
    Item 8: In-app logistics & transport request workflow.
    Status flow: requested -> accepted -> in_transit -> delivered.
    """
    __tablename__ = "transport_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Requester (farmer or buyer)
    transporter_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Transporter who accepts
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=True, index=True)
    pickup_location = Column(String, nullable=False)
    drop_location = Column(String, nullable=False)
    weight_quintals = Column(Float, nullable=False)
    preferred_date = Column(String, nullable=False)
    status = Column(String, default="requested", index=True)  # "requested", "accepted", "in_transit", "delivered"
    driver_notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requester = relationship("User", foreign_keys=[user_id])
    transporter = relationship("User", foreign_keys=[transporter_id])


class PaymentOrder(Base):
    """
    Item 9: Razorpay payment order tracking (Test Mode record).
    Status: created -> paid -> failed -> refunded.
    """
    __tablename__ = "payment_orders"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    razorpay_order_id = Column(String, unique=True, index=True, nullable=False)
    razorpay_payment_id = Column(String, nullable=True)
    amount_inr = Column(Float, nullable=False)
    status = Column(String, default="created", index=True)  # "created", "paid", "failed", "refunded"
    is_test_mode = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    offer = relationship("Offer", back_populates="payment_orders")
    buyer = relationship("User")
