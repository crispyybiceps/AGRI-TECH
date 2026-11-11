"""
Database Seed Script for AGRI-TECH.
Pre-populates database with demo farmer, farms, soil records, listings, demo buyer, and admin.
Run with: python seed.py
"""

import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base, SessionLocal
from app.models import (
    User, Farm, SoilRecord, WeatherCache, ChatSession, ChatMessage,
    MarketPrice, Listing, Offer, TransportRequest, PaymentOrder,
    SensorDevice, SensorReading, OTP
)
from app.services.mandi_service import DEFAULT_MAHARASHTRA_MANDIS
from app.services.soil_service import interpret_soil_health_card, interpret_visual_observation
from app.auth import get_password_hash


def seed_database():
    print("🌱 Seeding AGRI-TECH database...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Clean existing records in foreign-key safe order
        db.query(PaymentOrder).delete()
        db.query(TransportRequest).delete()
        db.query(Offer).delete()
        db.query(Listing).delete()
        db.query(ChatMessage).delete()
        db.query(ChatSession).delete()
        db.query(SensorReading).delete()
        db.query(SensorDevice).delete()
        db.query(SoilRecord).delete()
        db.query(WeatherCache).delete()
        db.query(Farm).delete()
        db.query(OTP).delete()
        db.query(User).delete()
        db.query(MarketPrice).delete()
        db.commit()

        # 2. Seed Users (default demo password: password123)
        demo_pwd_hash = get_password_hash("password123")
        farmer = User(
            phone="+919876543210",
            name="Ramesh Patil (रमेश पाटील)",
            password_hash=demo_pwd_hash,
            language_preference="mr",
            role="farmer",
            is_verified=True,
            rating=4.9
        )
        buyer = User(
            phone="+919888877777",
            name="Kailash Agro Traders (कैलास ॲग्रो ट्रेडर्स)",
            password_hash=demo_pwd_hash,
            language_preference="mr",
            role="buyer",
            is_verified=True,
            rating=5.0
        )
        admin = User(
            phone="+919999900000",
            name="KVK Admin Officer",
            password_hash=demo_pwd_hash,
            language_preference="en",
            role="admin",
            is_verified=True,
            rating=5.0
        )
        db.add_all([farmer, buyer, admin])
        db.commit()
        db.refresh(farmer)
        db.refresh(buyer)
        db.refresh(admin)
        print(f"✅ Users seeded: Farmer (ID: {farmer.id}), Buyer (ID: {buyer.id}), Admin (ID: {admin.id})")

        # 3. Seed Farms
        farm1 = Farm(
            user_id=farmer.id,
            name="Shree Ganesh Farm (श्री गणेश शेत)",
            village="Baramati (बारामती)",
            latitude=18.1512,
            longitude=74.5789,
            size_acres=4.5,
            crops="Sugarcane, Soybean"
        )
        farm2 = Farm(
            user_id=farmer.id,
            name="North Onion Plot (उत्तर कांदा वावर)",
            village="Lasalgaon (लासलगाव)",
            latitude=20.1465,
            longitude=74.2255,
            size_acres=2.5,
            crops="Onion, Wheat"
        )
        db.add_all([farm1, farm2])
        db.commit()
        db.refresh(farm1)
        db.refresh(farm2)
        print(f"✅ Farms seeded: {farm1.name}, {farm2.name}")

        # 4. Seed Tier 1 Soil Health Card (High Confidence)
        card_values = {"ph": 7.4, "ec": 0.42, "oc": 0.65, "n": 290.0, "p": 22.0, "k": 240.0}
        interp1 = interpret_soil_health_card(card_values, crop="Sugarcane")
        soil_rec1 = SoilRecord(
            farm_id=farm1.id,
            tier=1,
            source="Government Soil Health Card (Lab Test)",
            confidence="High",
            values_json=json.dumps(card_values),
            interpretation_json=json.dumps(interp1)
        )

        # Seed Tier 3 Visual Observation (Low Confidence)
        obs_values = {
            "color": "black_dark",
            "texture": "clay_sticky",
            "drainage": "moderate_24h",
            "cracking": "deep_cracks",
            "symptom": "yellow_lower_leaves"
        }
        interp3 = interpret_visual_observation(obs_values)
        soil_rec3 = SoilRecord(
            farm_id=farm2.id,
            tier=3,
            source="Guided Visual Field Observation",
            confidence="Low",
            values_json=json.dumps(obs_values),
            interpretation_json=json.dumps(interp3)
        )
        db.add_all([soil_rec1, soil_rec3])
        db.commit()
        print("✅ Tiered Soil Records seeded (Tier 1 Lab Card & Tier 3 Observation)")

        # 5. Seed Mandi Prices
        for item in DEFAULT_MAHARASHTRA_MANDIS:
            db.add(MarketPrice(**item))
        db.commit()
        print(f"✅ Mandi Reference Prices seeded ({len(DEFAULT_MAHARASHTRA_MANDIS)} APMCs)")

        # 6. Seed Direct Listings
        listing1 = Listing(
            farmer_id=farmer.id,
            crop="Soybean (JS-335)",
            quantity_quintals=50.0,
            quality_grade="Grade A (Premium)",
            expected_price=4750.0,
            location="Baramati, Pune",
            photos_json=json.dumps([]),
            status="active"
        )
        listing2 = Listing(
            farmer_id=farmer.id,
            crop="Onion (Garva / Red)",
            quantity_quintals=75.0,
            quality_grade="Grade A (Premium)",
            expected_price=1900.0,
            location="Lasalgaon, Nashik",
            photos_json=json.dumps([]),
            status="active"
        )
        db.add_all([listing1, listing2])
        db.commit()
        db.refresh(listing1)
        db.refresh(listing2)
        print(f"✅ Direct Crop Listings seeded: {listing1.crop}, {listing2.crop}")

        # 7. Seed Buyer Offer (Lifecycle: offer_made -> confirmed)
        offer1 = Offer(
            listing_id=listing1.id,
            buyer_id=buyer.id,
            offered_price=4700.0,
            quantity=35.0,
            status="confirmed",
            buyer_notes="Certified buyer pickup arranged via local transport."
        )
        db.add(offer1)
        db.commit()
        print("✅ Buyer Offer workflow seeded (Status: Confirmed)")

        # 8. Seed Chat Session with Flagged Message QA
        session1 = ChatSession(
            user_id=farmer.id,
            title="Pesticide & Spray Query"
        )
        db.add(session1)
        db.commit()
        db.refresh(session1)

        msg1 = ChatMessage(
            session_id=session1.id,
            sender="user",
            content="Can I spray Monocrotophos on my vegetable crop for caterpillar attack?"
        )
        msg2 = ChatMessage(
            session_id=session1.id,
            sender="assistant",
            content="⚠️ **Strictly Banned Chemical Alert:** 'Monocrotophos' is completely BANNED in India under the Insecticides Act. It causes severe neurotoxicity to humans and livestock.\n\n👉 **Recommended Action:** Use safe CIB&RC approved alternatives like Chlorantraniliprole 18.5% SC (0.3 ml/L) or Neem Oil (Azadirachtin 10,000 ppm at 2.5 ml/L). Always wear face mask and rubber gloves.",
            sources_json=json.dumps(["cibrc_pesticides_and_ipm.md"]),
            is_flagged=False
        )
        msg3 = ChatMessage(
            session_id=session1.id,
            sender="user",
            content="Is it safe to spray pesticides today?"
        )
        msg4 = ChatMessage(
            session_id=session1.id,
            sender="assistant",
            content="☀️ **Weather is favorable for spraying today.**\n\nWind speed is moderate with no heavy rain forecast. Spray during cool morning hours (7-10 AM) and observe pre-harvest intervals.",
            sources_json=json.dumps(["cibrc_pesticides_and_ipm.md"]),
            is_flagged=True,
            flag_reason="Farmer requested verification of wind threshold."
        )
        db.add_all([msg1, msg2, msg3, msg4])
        db.commit()
        print("✅ Chat Sessions and Flagged QA message seeded")

        print("\n🎉 AGRI-TECH SEED COMPLETED SUCCESSFULLY!\n")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

