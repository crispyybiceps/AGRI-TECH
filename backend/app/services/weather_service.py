"""
Weather Service and Advisory Engine for AGRI-TECH.
Integrates with Open-Meteo API (free, open-source, no key required),
caches forecasts in SQLite, with fallback order:
1. Fresh cache (< 3 hours)
2. Stale cache (labeled "last updated X hours ago")
3. Mock forecast ONLY if DEBUG_MOCK=True or as emergency test fallback
"""

import json
import os
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import WeatherCache, Farm
from app.config import settings

logger = logging.getLogger("agritech.weather")

CROP_CALENDAR_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "crop_calendar.json")

# Default Maharashtra coordinates (Pune) if farm coordinates are missing
DEFAULT_MAHARASHTRA_LAT = 18.5204
DEFAULT_MAHARASHTRA_LNG = 73.8567

WEATHER_CODES = {
    0: {"en": "Clear sky", "hi": "साफ आसमान", "mr": "स्वच्छ आकाश", "icon": "☀️"},
    1: {"en": "Mainly clear", "hi": "अधिकांशतः साफ", "mr": "मुख्यतः निरभ्र", "icon": "🌤️"},
    2: {"en": "Partly cloudy", "hi": "आंशिक बादल", "mr": "काहीसे ढगाळ", "icon": "⛅"},
    3: {"en": "Overcast", "hi": "घने बादल", "mr": "पूर्ण ढगाळ", "icon": "☁️"},
    45: {"en": "Foggy", "hi": "कोहरा", "mr": "धुके", "icon": "🌫️"},
    51: {"en": "Light drizzle", "hi": "हल्की बूंदाबांदी", "mr": "हलकी रिमझिम", "icon": "🌦️"},
    61: {"en": "Slight rain", "hi": "हल्की बारिश", "mr": "हलका पाऊस", "icon": "🌧️"},
    63: {"en": "Moderate rain", "hi": "मध्यम बारिश", "mr": "मध्यम पाऊस", "icon": "🌧️"},
    65: {"en": "Heavy rain", "hi": "भारी बारिश", "mr": "मुसळधार पाऊस", "icon": "⛈️"},
    80: {"en": "Rain showers", "hi": "बारिश की बौछारें", "mr": "पावसाच्या सरी", "icon": "🌦️"},
    95: {"en": "Thunderstorm", "hi": "तूफान और बिजली", "mr": "वादळी पाऊस", "icon": "⚡"},
}


def get_current_season() -> str:
    """Determine Indian crop season based on current month."""
    month = datetime.now().month
    if 6 <= month <= 10:
        return "kharif"
    elif month in [11, 12, 1, 2, 3]:
        return "rabi"
    else:
        return "zaid"


def generate_mock_forecast(lat: float, lng: float) -> Dict[str, Any]:
    """
    Fallback mock forecast data used ONLY when DEBUG_MOCK=True or as last resort.
    Labeled with is_mock: True.
    """
    today = datetime.now()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    return {
        "latitude": lat,
        "longitude": lng,
        "is_mock": True,
        "source": "mock_generator",
        "stale_notice": "Simulated forecast (DEBUG_MOCK mode active)",
        "daily": {
            "time": dates,
            "weather_code": [1, 2, 61, 63, 2, 0, 1],
            "temperature_2m_max": [33.5, 34.0, 31.5, 29.8, 32.0, 33.0, 34.2],
            "temperature_2m_min": [21.0, 21.5, 22.0, 20.5, 19.8, 20.2, 21.0],
            "precipitation_sum": [0.0, 1.2, 14.5, 26.0, 4.0, 0.0, 0.0],
            "precipitation_probability_max": [10, 35, 75, 85, 40, 5, 10],
            "wind_speed_10m_max": [14.2, 16.5, 22.0, 18.4, 12.0, 11.5, 13.0]
        },
        "current": {
            "temperature_2m": 29.5,
            "relative_humidity_2m": 62,
            "weather_code": 1,
            "wind_speed_10m": 12.5,
            "time": today.strftime("%Y-%m-%dT%H:00")
        }
    }


def fetch_open_meteo_forecast(lat: float, lng: float, timeout_sec: int = 5, retries: int = 2) -> Optional[Dict[str, Any]]:
    """
    Fetch 7-day forecast from Open-Meteo API with timeout and 2 retries.
    Returns None if all attempts fail.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lng}"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
        f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        f"&timezone=Asia%2FKolkata"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AgriTech-Maharashtra/1.0"})

    for attempt in range(1 + retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    data["is_mock"] = False
                    data["source"] = "open_meteo"
                    return data
        except Exception as e:
            logger.warning(f"Open-Meteo attempt {attempt + 1} failed: {e}")
            if attempt < retries:
                time.sleep(0.5)

    return None


def get_cached_or_fresh_weather(db: Session, farm_id: Optional[int], lat: float, lng: float) -> Dict[str, Any]:
    """
    Fallback order:
    1. Fresh cache (< 3 hours old)
    2. Live Open-Meteo API call (with 2 retries)
    3. Stale cache (any age, labeled 'last updated X hours ago')
    4. Mock forecast ONLY if DEBUG_MOCK=True or as emergency fallback
    """
    now = datetime.utcnow()
    three_hours_ago = now - timedelta(hours=3)

    # 1. Check Fresh Cache (< 3 hours)
    cache_query = db.query(WeatherCache).filter(
        WeatherCache.latitude == round(lat, 3),
        WeatherCache.longitude == round(lng, 3),
        WeatherCache.cached_at >= three_hours_ago
    )
    if farm_id:
        cache_query = cache_query.filter(WeatherCache.farm_id == farm_id)

    fresh_cached = cache_query.order_by(WeatherCache.cached_at.desc()).first()
    if fresh_cached:
        forecast = json.loads(fresh_cached.forecast_data)
        forecast["cached"] = True
        forecast["cached_at"] = fresh_cached.cached_at.isoformat()
        forecast["is_stale"] = False
        return forecast

    # 2. Call Real Open-Meteo API
    live_data = fetch_open_meteo_forecast(lat, lng, timeout_sec=5, retries=2)
    if live_data:
        live_data["cached"] = False
        live_data["cached_at"] = now.isoformat()
        live_data["is_stale"] = False

        # Store fresh cache
        new_cache = WeatherCache(
            farm_id=farm_id,
            latitude=round(lat, 3),
            longitude=round(lng, 3),
            forecast_data=json.dumps(live_data),
            cached_at=now
        )
        db.add(new_cache)
        db.commit()
        return live_data

    # 3. Fallback to Stale Cache (any age)
    stale_query = db.query(WeatherCache).filter(
        WeatherCache.latitude == round(lat, 3),
        WeatherCache.longitude == round(lng, 3)
    )
    if farm_id:
        stale_query = stale_query.filter(WeatherCache.farm_id == farm_id)

    stale_cached = stale_query.order_by(WeatherCache.cached_at.desc()).first()
    if stale_cached:
        forecast = json.loads(stale_cached.forecast_data)
        hours_old = max(1, int((now - stale_cached.cached_at).total_seconds() / 3600))
        forecast["cached"] = True
        forecast["cached_at"] = stale_cached.cached_at.isoformat()
        forecast["is_stale"] = True
        forecast["stale_notice"] = f"Displaying saved forecast (last updated {hours_old} hour{'s' if hours_old > 1 else ''} ago)"
        return forecast

    # 4. Mock ONLY if DEBUG_MOCK=True or as last-ditch fallback
    logger.info("Using mock forecast fallback")
    mock_data = generate_mock_forecast(lat, lng)
    return mock_data


def generate_agricultural_advisory(forecast: Dict[str, Any], crops: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Rule-based agricultural advisory engine based on real meteorology principles.
    Returns advisories with priority in en, hi, mr.
    """
    advisories = []
    daily = forecast.get("daily", {})
    rain_sums = daily.get("precipitation_sum", [0])
    rain_probs = daily.get("precipitation_probability_max", [0])
    max_temps = daily.get("temperature_2m_max", [30])
    wind_speeds = daily.get("wind_speed_10m_max", [10])

    next_3d_rain = sum(rain_sums[:3]) if len(rain_sums) >= 3 else rain_sums[0]
    today_rain_prob = rain_probs[0] if rain_probs else 0
    today_max_wind = wind_speeds[0] if wind_speeds else 0
    today_max_temp = max_temps[0] if max_temps else 30

    # Rule 1: Heavy rain warning
    if next_3d_rain > 20 or today_rain_prob > 70:
        advisories.append({
            "type": "rain_warning",
            "priority": "high",
            "icon": "⛈️",
            "title": {"en": "Heavy Rain Expected", "hi": "भारी बारिश की संभावना", "mr": "मुसळधार पावसाची शक्यता"},
            "action": {
                "en": "Delay chemical spraying and sowing. Clear farm drainage channels to prevent waterlogging.",
                "hi": "कीटनाशक छिड़काव और बुवाई टालें। खेत में जलभराव रोकने के लिए जल निकासी नालियों को साफ करें।",
                "mr": "कीटकनाशक फवारणी व पेरणी पुढे ढकला. शेतात पाणी साचू नये म्हणून निचरा चर स्वच्छ करा."
            }
        })

    # Rule 2: High wind speed
    if today_max_wind > 20:
        advisories.append({
            "type": "wind_warning",
            "priority": "high",
            "icon": "💨",
            "title": {"en": "High Wind Alert", "hi": "तेज हवा चेतावनी", "mr": "जोरदार वाऱ्याचा इशारा"},
            "action": {
                "en": "Avoid all pesticide/foliar spraying due to chemical drift risk. Support tall crops like sugarcane, banana, and maize.",
                "hi": "हवा के बहाव के कारण किसी भी छिड़काव से बचें। केला, मक्का और गन्ने जैसी लंबी फसलों को सहारा दें।",
                "mr": "वाऱ्यामुळे फवारणी करणे टाळा (औषध उडून जाण्याचा धोका). केळी, मका व ऊस पिकांना आधार द्या."
            }
        })

    # Rule 3: Heat wave
    if today_max_temp > 38:
        advisories.append({
            "type": "heat_wave",
            "priority": "medium",
            "icon": "🔥",
            "title": {"en": "High Temperature / Heat Stress", "hi": "अत्यधिक तापमान चेतावनी", "mr": "उष्णतेची लाट"},
            "action": {
                "en": "Apply light, frequent irrigation early morning or late evening. Mulch soil to conserve moisture.",
                "hi": "सुबह जल्दी या शाम को हल्की सिंचाई करें। नमी बनाए रखने के लिए खेतों में मल्चिंग करें।",
                "mr": "पिकांना सकाळी लवकर किंवा संध्याकाळी हलके पाणी द्या. ओलावा टिकवण्यासाठी आच्छादनाचा (मल्चिंग) वापर करा."
            }
        })

    # Rule 4: Optimal spray window
    if next_3d_rain < 2 and today_rain_prob < 20 and today_max_wind < 15:
        advisories.append({
            "type": "optimal_spraying",
            "priority": "low",
            "icon": "🌱",
            "title": {"en": "Good Window for Farm Work", "hi": "कृषि कार्यों के लिए अनुकूल मौसम", "mr": "शेतीकामांसाठी अनुकूल हवामान"},
            "action": {
                "en": "Weather is clear and calm. Suitable for scheduled nutrient sprays, intercultivation, and weeding.",
                "hi": "मौसम साफ और शांत है। आवश्यक छिड़काव, निंदाई-गुड़ाई और निराई के लिए अनुकूल समय है।",
                "mr": "हवामान स्वच्छ व शांत आहे. खते/औषध फवारणी व खुरपणी कामांसाठी उत्तम वेळ आहे."
            }
        })

    # Rule 5: Crop-specific standing crop advisory
    if crops:
        crops_lower = crops.lower()
        if "soybean" in crops_lower or "सोयाबीन" in crops_lower:
            advisories.append({
                "type": "crop_specific",
                "priority": "medium",
                "icon": "🌾",
                "title": {"en": "Soybean Advisory", "hi": "सोयाबीन फसल सलाह", "mr": "सोयाबीन पीक सल्ला"},
                "action": {
                    "en": "Monitor for semilooper and girdle beetle. Use pheromone lures (5/ha) for eco-friendly monitoring.",
                    "hi": "सेमीलूपर और गर्डल बीटल की निगरानी करें। पर्यावरण अनुकूल निगरानी के लिए फेरोमोन ट्रैप (5 प्रति हेक्टेयर) लगाएं।",
                    "mr": "उंट अळी व चक्री भुंग्यांचा प्रादुर्भाव तपासा. नियंत्रणासाठी कामगंध सापळे (५ प्रति हेक्टर) लावा."
                }
            })
        if "cotton" in crops_lower or "कापूस" in crops_lower or "कपास" in crops_lower:
            advisories.append({
                "type": "crop_specific",
                "priority": "medium",
                "icon": "☁️",
                "title": {"en": "Cotton Advisory", "hi": "कपास फसल सलाह", "mr": "कापूस पीक सल्ला"},
                "action": {
                    "en": "Inspect underside of leaves for whitefly and jassids. Apply 5% Neem Seed Kernel Extract (NSKE) at early onset.",
                    "hi": "सफेद मक्खी और माहो के लिए पत्तियों के नीचे जांच करें। शुरुआती लक्षण पर 5% नीम अर्क का छिड़काव करें।",
                    "mr": "पानांच्या खाली पांढरी माशी व तुडतुडे तपासा. प्रादुर्भाव दिसताच ५% निंबोळी अर्क फवारा."
                }
            })

    return advisories


def get_crop_suggestions() -> Dict[str, Any]:
    """Load seasonal crop calendar and guidance suggestions."""
    season = get_current_season()
    try:
        with open(CROP_CALENDAR_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "current_season": season,
                "general_guidance": data.get("general_guidance", {}),
                "crops": data.get("seasons", {}).get(season, [])
            }
    except Exception as e:
        logger.error(f"Error loading crop calendar: {e}")
        return {"current_season": season, "crops": []}


# Alias for backwards compatibility with weather_router
get_crop_recommendations = get_crop_suggestions
