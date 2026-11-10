"""
Mandi Price and Agmarknet Service for AGRI-TECH.
Provides:
- Real integration with data.gov.in Agmarknet daily mandi price API
- Daily synchronization into market_prices table
- Fallback hierarchy: Live data.gov.in -> Last cached with date -> Static labeled mock dataset
- Real-time price fairness engine (fair / below / above)
"""

import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import MarketPrice
from app.config import settings

logger = logging.getLogger("agritech.mandi")

# Benchmark dataset across prominent Maharashtra APMCs
DEFAULT_MAHARASHTRA_MANDIS = [
    {
        "commodity": "Soybean (Yellow)",
        "mandi_name": "Latur APMC",
        "district": "Latur",
        "min_price": 4350.0,
        "max_price": 4850.0,
        "modal_price": 4650.0,
        "unit": "Rs/quintal",
        "arrival_date": datetime.now().strftime("%Y-%m-%d"),
        "is_mock": True,
        "source": "mock"
    },
    {
        "commodity": "Cotton (Medium Staple)",
        "mandi_name": "Akola APMC",
        "district": "Akola",
        "min_price": 6800.0,
        "max_price": 7500.0,
        "modal_price": 7250.0,
        "unit": "Rs/quintal",
        "arrival_date": datetime.now().strftime("%Y-%m-%d"),
        "is_mock": True,
        "source": "mock"
    },
    {
        "commodity": "Onion (Red / Garva)",
        "mandi_name": "Lasalgaon Mandi",
        "district": "Nashik",
        "min_price": 1400.0,
        "max_price": 2250.0,
        "modal_price": 1850.0,
        "unit": "Rs/quintal",
        "arrival_date": datetime.now().strftime("%Y-%m-%d"),
        "is_mock": True,
        "source": "mock"
    },
    {
        "commodity": "Bengal Gram / Chana",
        "mandi_name": "Baramati APMC",
        "district": "Pune",
        "min_price": 5100.0,
        "max_price": 5650.0,
        "modal_price": 5400.0,
        "unit": "Rs/quintal",
        "arrival_date": datetime.now().strftime("%Y-%m-%d"),
        "is_mock": True,
        "source": "mock"
    },
    {
        "commodity": "Wheat (Lokwan / Sharbati)",
        "mandi_name": "Pune Gultekdi APMC",
        "district": "Pune",
        "min_price": 2600.0,
        "max_price": 3100.0,
        "modal_price": 2850.0,
        "unit": "Rs/quintal",
        "arrival_date": datetime.now().strftime("%Y-%m-%d"),
        "is_mock": True,
        "source": "mock"
    },
    {
        "commodity": "Pigeon Pea / Tur (Red)",
        "mandi_name": "Jalna APMC",
        "district": "Jalna",
        "min_price": 8900.0,
        "max_price": 10200.0,
        "modal_price": 9650.0,
        "unit": "Rs/quintal",
        "arrival_date": datetime.now().strftime("%Y-%m-%d"),
        "is_mock": True,
        "source": "mock"
    },
    {
        "commodity": "Banana (Grand Naine)",
        "mandi_name": "Jalgaon APMC",
        "district": "Jalgaon",
        "min_price": 1100.0,
        "max_price": 1800.0,
        "modal_price": 1450.0,
        "unit": "Rs/quintal",
        "arrival_date": datetime.now().strftime("%Y-%m-%d"),
        "is_mock": True,
        "source": "mock"
    },
    {
        "commodity": "Jowar / Sorghum (Maldandi)",
        "mandi_name": "Solapur Mandi",
        "district": "Solapur",
        "min_price": 3200.0,
        "max_price": 4100.0,
        "modal_price": 3700.0,
        "unit": "Rs/quintal",
        "arrival_date": datetime.now().strftime("%Y-%m-%d"),
        "is_mock": True,
        "source": "mock"
    }
]


def fetch_live_agmarknet_prices(state: str = "Maharashtra", limit: int = 50) -> Optional[List[Dict[str, Any]]]:
    """
    Item 7: Real integration with data.gov.in Agmarknet daily mandi price API.
    Uses DATA_GOV_API_KEY and AGMARKNET_RESOURCE_ID.
    """
    if not settings.DATA_GOV_API_KEY:
        logger.info("DATA_GOV_API_KEY not configured; using cached/mock mandi prices")
        return None

    query_params = urllib.parse.urlencode({
        "api-key": settings.DATA_GOV_API_KEY,
        "format": "json",
        "limit": limit,
        "filters[state]": state
    })
    url = f"https://api.data.gov.in/resource/{settings.AGMARKNET_RESOURCE_ID}?{query_params}"

    req = urllib.request.Request(url, headers={"User-Agent": "AgriTech-App/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                raw_data = json.loads(response.read().decode("utf-8"))
                records = raw_data.get("records", [])
                parsed = []
                for rec in records:
                    try:
                        modal_val = float(rec.get("modal_price", 0))
                        min_val = float(rec.get("min_price", modal_val * 0.9))
                        max_val = float(rec.get("max_price", modal_val * 1.1))
                        if modal_val > 0:
                            parsed.append({
                                "commodity": rec.get("commodity", "General Crop"),
                                "mandi_name": rec.get("market", "APMC Market"),
                                "district": rec.get("district", "Maharashtra"),
                                "min_price": min_val,
                                "max_price": max_val,
                                "modal_price": modal_val,
                                "unit": "Rs/quintal",
                                "arrival_date": rec.get("arrival_date", datetime.now().strftime("%Y-%m-%d")),
                                "is_mock": False,
                                "source": "live"
                            })
                    except (ValueError, TypeError):
                        continue
                if parsed:
                    return parsed
    except Exception as e:
        logger.warning(f"data.gov.in Agmarknet API call failed: {e}")

    return None


def sync_mandi_prices_task(db: Session, state: str = "Maharashtra") -> Dict[str, Any]:
    """
    Background sync task: Fetch live Agmarknet prices, insert/update in database.
    Fallback hierarchy: Live data.gov.in -> Last cached -> Static mock.
    """
    live_records = fetch_live_agmarknet_prices(state=state)
    if live_records:
        # Save live records
        for rec in live_records:
            existing = (
                db.query(MarketPrice)
                .filter(
                    MarketPrice.commodity == rec["commodity"],
                    MarketPrice.mandi_name == rec["mandi_name"]
                )
                .first()
            )
            if existing:
                existing.min_price = rec["min_price"]
                existing.max_price = rec["max_price"]
                existing.modal_price = rec["modal_price"]
                existing.arrival_date = rec["arrival_date"]
                existing.is_mock = False
                existing.source = "live"
            else:
                new_entry = MarketPrice(**rec)
                db.add(new_entry)
        db.commit()
        return {"status": "success", "source": "live", "count": len(live_records)}

    # Fallback to cached or seed mock
    count = db.query(MarketPrice).count()
    if count == 0:
        seed_mandi_prices_if_empty(db)
        return {"status": "fallback_seed", "source": "mock", "count": len(DEFAULT_MAHARASHTRA_MANDIS)}

    return {"status": "cached", "source": "cached", "count": count}


def seed_mandi_prices_if_empty(db: Session):
    """Seed benchmark Maharashtra Mandi prices if the table is empty."""
    count = db.query(MarketPrice).count()
    if count == 0:
        for m in DEFAULT_MAHARASHTRA_MANDIS:
            entry = MarketPrice(
                commodity=m["commodity"],
                mandi_name=m["mandi_name"],
                district=m["district"],
                min_price=m["min_price"],
                max_price=m["max_price"],
                modal_price=m["modal_price"],
                unit=m["unit"],
                arrival_date=m["arrival_date"],
                is_mock=m.get("is_mock", True),
                source=m.get("source", "mock")
            )
            db.add(entry)
        db.commit()


def compare_farmer_price_to_mandi(
    db: Session,
    crop: str,
    expected_price: float
) -> Dict[str, Any]:
    """
    Compare farmer's expected listing price against prevailing modal Mandi prices.
    Returns visual indicators: 'below', 'fair', 'above'.
    """
    crop_clean = crop.strip().lower()
    prices = db.query(MarketPrice).all()

    matched_price = None
    for p in prices:
        if crop_clean in p.commodity.lower() or p.commodity.lower() in crop_clean:
            matched_price = p
            break

    if not matched_price and prices:
        matched_price = prices[0]

    if not matched_price:
        return {
            "indicator": "fair",
            "mandi_modal": expected_price,
            "diff_percentage": 0.0,
            "advice_en": "Competitive price.",
            "advice_hi": "उचित मूल्य।",
            "advice_mr": "रास्त भाव."
        }

    modal = matched_price.modal_price
    diff_pct = round(((expected_price - modal) / modal) * 100, 1)

    if diff_pct < -10.0:
        indicator = "below"
        advice_en = f"You are pricing below the current Mandi modal average (Rs {modal} / quintal). Consider asking higher."
        advice_hi = f"आप मंडी औसत (रु {modal}) से कम भाव मांग रहे हैं। थोड़ा अधिक मूल्य रखने पर विचार करें।"
        advice_mr = f"तुम्ही सध्याच्या बाजार समिती सरासरीपेक्षा (रु {modal}) कमी दर सांगत आहात. थोडा जास्त दर मागू शकता."
    elif -10.0 <= diff_pct <= 15.0:
        indicator = "fair"
        advice_en = f"Fair market price! Your price aligns closely with the current Mandi modal average of Rs {modal} / quintal."
        advice_hi = f"उचित और प्रतिस्पर्धी भाव! आपका मूल्य मंडी औसत (रु {modal}) के अनुकूल है।"
        advice_mr = f"रास्त व स्पर्धात्मक भाव! तुमचा दर सध्याच्या बाजारभाव सरासरीशी (रु {modal}) अगदी जुळणारा आहे."
    else:
        indicator = "above"
        advice_en = f"Premium price ({diff_pct}% above Mandi modal rate of Rs {modal}). Only suitable for certified Grade A produce."
        advice_hi = f"प्रीमियम मूल्य (मंडी दर रु {modal} से {diff_pct}% अधिक)। केवल उत्कृष्ट ग्रेड A फसल के लिए उपयुक्त।"
        advice_mr = f"जास्त दर (बाजार समिती सरासरी रु {modal} पेक्षा {diff_pct}% अधिक). केवळ उच्च प्रतीच्या (ग्रेड A) शेतमालासाठी योग्य."

    return {
        "indicator": indicator,
        "mandi_modal": modal,
        "mandi_name": matched_price.mandi_name,
        "commodity": matched_price.commodity,
        "diff_percentage": diff_pct,
        "is_mock": matched_price.is_mock,
        "source": matched_price.source,
        "arrival_date": matched_price.arrival_date,
        "advice_en": advice_en,
        "advice_hi": advice_hi,
        "advice_mr": advice_mr
    }
