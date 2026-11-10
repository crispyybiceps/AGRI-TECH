"""
Soil Module Service for AGRI-TECH.
Provides tiered soil interpretation:
- Tier 1: Lab Soil Health Card analysis (High confidence)
- Tier 2: ISRIC SoilGrids v2 REST API (30-day SQLite caching, rate limiting backoff, ESTIMATE label)
- Tier 3: Guided visual field observations (Low confidence, 'Possible indication of...')
- Tier 4: Anomaly validation for sensor readings
- Tier 5: Labs directory & sample collection steps
- OCR Vision Engine: Claude Vision API with strict JSON schema and ranges validation
"""

import json
import os
import time
import math
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger("agritech.soil")

STANDARDS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "soil_standards.json")
LABS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "maharashtra_soil_labs.json")


def load_soil_standards() -> Dict[str, Any]:
    with open(STANDARDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_soil_labs() -> Dict[str, Any]:
    with open(LABS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def interpret_soil_health_card(values: Dict[str, float], crop: Optional[str] = None) -> Dict[str, Any]:
    """
    Tier 1 (High Confidence): Interprets parameters from official lab test.
    Categorizes pH, EC, OC, N, P, K into Low/Medium/High and provides amendments.
    """
    standards = load_soil_standards()
    param_configs = standards.get("parameters", {})
    amendments_configs = standards.get("amendments", {})

    interpreted_params = {}
    recommendations = []
    fertilizer_adjustments = []

    # 1. Parameter status classification
    for key, val in values.items():
        if key in param_configs and val is not None:
            config = param_configs[key]
            matched_status = "Normal"
            matched_hi = "सामान्य"
            matched_mr = "सामान्य"
            color = "green"

            for r in config.get("ranges", []):
                min_val = r.get("min")
                max_val = r.get("max")
                if min_val is not None and max_val is not None:
                    if min_val <= val < max_val:
                        matched_status = r["status"]
                        matched_hi = r.get("status_hi", matched_status)
                        matched_mr = r.get("status_mr", matched_status)
                        color = r.get("color", "green")
                        break
                elif min_val is not None and val >= min_val:
                    matched_status = r["status"]
                    matched_hi = r.get("status_hi", matched_status)
                    matched_mr = r.get("status_mr", matched_status)
                    color = r.get("color", "green")
                    break
                elif max_val is not None and val < max_val:
                    matched_status = r["status"]
                    matched_hi = r.get("status_hi", matched_status)
                    matched_mr = r.get("status_mr", matched_status)
                    color = r.get("color", "green")
                    break

            interpreted_params[key] = {
                "value": val,
                "unit": config.get("unit", ""),
                "status": matched_status,
                "status_hi": matched_hi,
                "status_mr": matched_mr,
                "color": color
            }

    # 2. Chemical amendment rules
    ph_val = values.get("ph")
    if ph_val is not None:
        if ph_val < 6.5:
            recommendations.append(amendments_configs.get("acidic_soil", {}))
        elif ph_val > 8.5:
            recommendations.append(amendments_configs.get("sodic_soil", {}))

    oc_val = values.get("oc")
    if oc_val is not None and oc_val < 0.5:
        recommendations.append(amendments_configs.get("low_organic_carbon", {}))

    # 3. Fertilizer NPK recommendations
    n_info = interpreted_params.get("n", {})
    p_info = interpreted_params.get("p", {})
    k_info = interpreted_params.get("k", {})

    if n_info.get("status") == "Low":
        fertilizer_adjustments.append({
            "en": "Nitrogen is LOW: Increase recommended Urea dosage by 25%. Apply in 2 split doses.",
            "hi": "नाइट्रोजन कम है: अनुशंसित यूरिया मात्रा 25% बढ़ाएं। दो खुराकों में दें।",
            "mr": "नत्र कमी आहे: युरियाची शिफारशीत मात्रा २५% वाढवा. दोन हप्त्यांमध्ये विभागून द्या."
        })
    elif n_info.get("status") == "High":
        fertilizer_adjustments.append({
            "en": "Nitrogen is HIGH: Reduce Urea by 20% to avoid excessive vegetative growth and pest susceptibility.",
            "hi": "नाइट्रोजन अधिक है: यूरिया 20% कम करें ताकि कीट प्रकोप न बढ़े।",
            "mr": "नत्र जास्त आहे: युरिया २०% कमी करा, जेणेकरून किडींचा प्रादुर्भाव वाढणार नाही."
        })

    if p_info.get("status") == "Low":
        fertilizer_adjustments.append({
            "en": "Phosphorus is LOW: Apply Single Super Phosphate (SSP) or DAP at basal sowing stage.",
            "hi": "फास्फोरस कम है: बुवाई के समय एसएसपी (SSP) या डीएपी (DAP) डालें।",
            "mr": "स्फुरद कमी आहे: पेरणीच्या वेळी सिंगल सुपर फॉस्फेट (SSP) किंवा DAP खत द्या."
        })

    if k_info.get("status") == "Low":
        fertilizer_adjustments.append({
            "en": "Potassium is LOW: Apply Muriate of Potash (MOP) to improve crop disease resistance.",
            "hi": "पोटाश कम है: फसल की रोग प्रतिरोधक क्षमता बढ़ाने हेतु एमओपी (MOP) का प्रयोग करें।",
            "mr": "पालाश कमी आहे: पिकांची रोगप्रतिकारक क्षमता वाढवण्यासाठी म्युरेट ऑफ पोटॅश (MOP) वापरा."
        })

    return {
        "parameters": interpreted_params,
        "amendments": recommendations,
        "fertilizer_adjustments": fertilizer_adjustments,
        "crop_context": crop or "Standing field crops"
    }


def get_soilgrids_estimate(lat: float, lng: float, db: Any = None) -> Dict[str, Any]:
    """
    Tier 2: ISRIC SoilGrids v2 REST query with 30-day cache & rate-limit handling.
    Always clearly labeled as ESTIMATE, not a lab test.
    """
    from datetime import datetime, timezone, timedelta
    from app.models import SoilRecord

    # Check 30-day cache if db session provided
    rounded_lat = round(lat, 2)
    rounded_lng = round(lng, 2)

    if db:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        cached_record = (
            db.query(SoilRecord)
            .filter(
                SoilRecord.tier == 2,
                SoilRecord.created_at >= thirty_days_ago
            )
            .order_by(SoilRecord.created_at.desc())
            .first()
        )
        if cached_record and cached_record.interpretation_json:
            try:
                data = json.loads(cached_record.interpretation_json)
                if abs(data.get("latitude", 0) - rounded_lat) < 0.05 and abs(data.get("longitude", 0) - rounded_lng) < 0.05:
                    data["cached"] = True
                    return data
            except Exception:
                pass

    # Call Real ISRIC SoilGrids v2 API
    url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lng}&lat={lat}&property=phh2o&property=soc&property=clay&property=sand&property=nitrogen&depth=0-30cm&value=mean"
    req = urllib.request.Request(url, headers={"User-Agent": "AgriTech-India/1.0"})

    parsed_layers = {}
    is_real = False

    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=6) as response:
                if response.status == 200:
                    raw = json.loads(response.read().decode("utf-8"))
                    layers = raw.get("properties", {}).get("layers", [])
                    for layer in layers:
                        name = layer.get("name")
                        depths = layer.get("depths", [])
                        if depths and "values" in depths[0]:
                            mean_val = depths[0]["values"].get("mean")
                            if mean_val is not None:
                                parsed_layers[name] = mean_val
                    is_real = True
                    break
                elif response.status == 429:
                    logger.warning("SoilGrids rate-limited (HTTP 429), backing off...")
                    time.sleep(1.0)
        except Exception as e:
            logger.warning(f"ISRIC SoilGrids API query attempt {attempt + 1} failed: {e}")
            time.sleep(0.5)

    if is_real and parsed_layers:
        # Scale ISRIC units: phh2o is pH*10, soc is dg/kg, nitrogen is cg/kg, clay is g/kg
        ph = round(parsed_layers.get("phh2o", 75) / 10.0, 1) if "phh2o" in parsed_layers else 7.5
        clay = round(parsed_layers.get("clay", 450) / 10.0, 1) if "clay" in parsed_layers else 45.0
        sand = round(parsed_layers.get("sand", 200) / 10.0, 1) if "sand" in parsed_layers else 20.0
        soc = round(parsed_layers.get("soc", 100) / 10.0, 1) if "soc" in parsed_layers else 10.0
        nitrogen = round(parsed_layers.get("nitrogen", 150) / 100.0, 2) if "nitrogen" in parsed_layers else 1.5

        result = {
            "tier": 2,
            "confidence": "Low to Medium",
            "source": "ISRIC SoilGrids v2 REST API (Real)",
            "is_mock": False,
            "latitude": rounded_lat,
            "longitude": rounded_lng,
            "disclaimer_en": "ESTIMATE, not a lab test. Satellite & geological models cannot replace laboratory chemical analysis.",
            "disclaimer_hi": "यह केवल एक अनुमान है, प्रयोगशाला परीक्षण नहीं। उपग्रह डेटा मिट्टी परीक्षण का विकल्प नहीं है।",
            "disclaimer_mr": "हा केवळ भौगोलिक अंदाज आहे, प्रयोगशाळेतील चाचणी नाही. सॅटेलाईट अंदाज लॅब टेस्टची जागा घेऊ शकत नाही.",
            "estimated_properties": {
                "ph": {"value": ph, "label": "Moderately Alkaline" if ph > 7.5 else ("Neutral" if ph >= 6.5 else "Acidic")},
                "clay_fraction": {"value": f"{clay}%", "label": "Heavy Clay / Vertisol" if clay > 40 else "Medium Clay"},
                "sand_fraction": {"value": f"{sand}%", "label": "Sand percentage"},
                "organic_carbon": {"value": f"{soc} g/kg", "label": "Estimated Organic Carbon"},
                "nitrogen": {"value": f"{nitrogen} g/kg", "label": "Estimated Total Nitrogen"}
            },
            "general_management_advice": {
                "en": "Deccan basalt regional profile: High clay content with high water retention capacity. Ensure adequate field drainage.",
                "hi": "दक्कन बेसाल्ट क्षेत्रीय प्रोफाइल: उच्च जल धारण क्षमता वाली मिट्टी। खेतों में जल निकासी नालियों की व्यवस्था रखें।",
                "mr": "दख्खन बेसॉल्ट प्रादेशिक प्रोफाइल: काळी कसदार जमीन, ओलावा टिकवून ठेवण्याची क्षमता जास्त. पाण्याचा निचरा योग्य ठेवा."
            }
        }
        return result

    # Fallback to labeled mock estimate
    logger.info("Using mock SoilGrids estimate fallback")
    return {
        "tier": 2,
        "confidence": "Low to Medium",
        "source": "ISRIC SoilGrids 250m Global Model (Fallback Mock)",
        "is_mock": True,
        "latitude": rounded_lat,
        "longitude": rounded_lng,
        "disclaimer_en": "ESTIMATE, not a lab test. Satellite & geological models cannot replace laboratory chemical analysis.",
        "disclaimer_hi": "यह केवल एक अनुमान है, प्रयोगशाला परीक्षण नहीं। उपग्रह डेटा मिट्टी परीक्षण का विकल्प नहीं है।",
        "disclaimer_mr": "हा केवळ भौगोलिक अंदाज आहे, प्रयोगशाळेतील चाचणी नाही. सॅटेलाईट अंदाज लॅब टेस्टची जागा घेऊ शकत नाही.",
        "estimated_properties": {
            "ph": {"value": 7.6, "label": "Moderately Alkaline", "confidence_range": "7.1 - 8.2"},
            "clay_fraction": {"value": "48%", "label": "High Clay (Heavy Black Soil / Vertisol)"},
            "organic_carbon_stock": {"value": "45 t/ha", "label": "Moderate Organic Matter"},
            "bulk_density": {"value": "1.32 g/cm³", "label": "Medium Compaction"}
        },
        "general_management_advice": {
            "en": "Typical black cotton soil: High water retention capacity, shrinks and cracks when dry. Ensure adequate drainage channels during heavy rains.",
            "hi": "विशिष्ट काली कपास मिट्टी: पानी सोखने की क्षमता अधिक। सूखने पर दरारें पड़ती हैं। खेत में जल निकासी की व्यवस्था रखें।",
            "mr": "पारंपारिक काळी कसदार जमीन (काळी कापसाची माती): ओलावा टिकवून ठेवण्याची क्षमता उत्तम. पाऊस जास्त झाल्यास पाण्याचा निचरा आवश्यक."
        }
    }


def interpret_visual_observation(obs: Dict[str, str]) -> Dict[str, Any]:
    """
    Tier 3 (Low Confidence): Guided farmer visual observations.
    Phrased strictly as 'Possible indication of...', never 'diagnosis'.
    """
    indications = []

    color = obs.get("color", "")
    texture = obs.get("texture", "")
    drainage = obs.get("drainage", "")
    cracking = obs.get("cracking", "")
    symptom = obs.get("symptom", "")

    # Color
    if color == "grey_white_crust":
        indications.append({
            "en": "White / grey crust on surface: Possible indication of soil salinity or accumulation of surface salts.",
            "hi": "सतह पर सफेद/धूसर पपड़ी: मिट्टी में खारापन (लवणता) का संभावित संकेत।",
            "mr": "जमिनीवर पांढरा/राखाडी थर: जमिनीत क्षार साचल्याचे (खारवट जमीन) संभाव्य लक्षण."
        })
    elif color == "pale_yellow":
        indications.append({
            "en": "Pale yellow / light color: Possible indication of low organic matter and depleted nitrogen.",
            "hi": "हल्का पीला रंग: कम जैविक खाद (ऑर्गेनिक कार्बन) और नाइट्रोजन की कमी का संभावित संकेत।",
            "mr": "फिकट पिवळसर रंग: सेंद्रिय कर्ब व नत्राचे प्रमाण खूप कमी असल्याचे संभाव्य लक्षण."
        })

    # Texture & Cracking
    if texture == "clay_sticky" and cracking == "deep_cracks":
        indications.append({
            "en": "Heavy sticky clay with deep cracks: Typical black cotton soil (Vertisol). High moisture retention, requires drainage management.",
            "hi": "गहरी दरारें और चिपचिपी मिट्टी: विशिष्ट काली मिट्टी (कपास हेतु उपयुक्त)। जल निकासी का ध्यान रखें।",
            "mr": "चिमट काळी माती व खोल भेगा: अस्सल काळी कापसाची जमीन. पाणी धरून ठेवण्याची क्षमता जास्त, निचऱ्याची गरज."
        })

    # Drainage
    if drainage == "waterlogs":
        indications.append({
            "en": "Frequent waterlogging: High risk of root rot and anaerobic conditions. Sub-surface drainage or raised beds recommended.",
            "hi": "पानी का ठहराव: जड़ सड़न का खतरा। ढलान वाली नालियां या उठी हुई क्यारियां बनाएं।",
            "mr": "पाणी साचून राहणे: मूळ कुजण्याचा धोका. शेतात चर काढून पाण्याचा निचरा करा किंवा गादीवाफे वापरा."
        })

    # Symptoms
    if symptom == "yellow_lower_leaves":
        indications.append({
            "en": "Yellowing lower leaves (chlorosis): Possible nitrogen or magnesium deficiency. Confirm with tissue or soil test.",
            "hi": "निचली पत्तियों का पीला पड़ना: नाइट्रोजन की कमी का संभावित संकेत। यूरिया या कम्पोस्ट खाद दें।",
            "mr": "खालची पाने पिवळी पडणे: नत्र (नायट्रोजन) कमतरतेचे संभाव्य लक्षण. खात्रीसाठी माती परीक्षण करा."
        })
    elif symptom == "purple_stems_leaves":
        indications.append({
            "en": "Purplish discoloration on stems/leaves: Possible phosphorus deficiency, common in cold or alkaline soils.",
            "hi": "पत्तियों या तनों का बैंगनी होना: फास्फोरस की कमी का संभावित संकेत।",
            "mr": "पाने व खोड जांभळट होणे: स्फुरद (फॉस्फरस) कमतरतेचे संभाव्य लक्षण."
        })

    return {
        "tier": 3,
        "confidence": "Low",
        "source": "Guided Field Observation",
        "disclaimer_en": "Observations are visual cues only. Always verify with an official laboratory Soil Health Card.",
        "disclaimer_hi": "यह केवल दृश्य निरीक्षण है। पुष्टि के लिए प्रयोगशाला परीक्षण कराएं।",
        "disclaimer_mr": "हे केवळ बाह्य लक्षणांवर आधारित निरीक्षण आहे. अचूक माहितीसाठी शासकीय लॅब टेस्ट करा.",
        "indications": indications
    }


def validate_soil_card_ranges(values: Dict[str, Any]) -> Dict[str, Any]:
    """Validates physical/chemical plausibility of extracted or entered Soil Health Card values."""
    limits = {
        "ph": (3.0, 11.0),
        "ec": (0.0, 20.0),
        "oc": (0.0, 10.0),
        "n": (0.0, 1500.0),
        "p": (0.0, 200.0),
        "k": (0.0, 1500.0),
        "sulphur": (0.0, 100.0),
        "zinc": (0.0, 50.0),
        "iron": (0.0, 100.0),
        "copper": (0.0, 50.0),
        "manganese": (0.0, 100.0),
        "boron": (0.0, 20.0),
    }
    validated = {}
    for k, (low, high) in limits.items():
        if k in values and values[k] is not None:
            try:
                v = float(values[k])
                if low <= v <= high:
                    validated[k] = v
                else:
                    logger.warning(f"Parameter {k}={v} out of plausible range [{low}, {high}]")
            except (ValueError, TypeError):
                pass
    return validated


def extract_soil_card_from_image_vision(base64_image: str, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """
    Item 3: Real Soil Health Card OCR using Claude Vision (Anthropic API).
    Extracts pH, EC, OC, N, P, K, S, Zn, Fe, Cu, Mn, B with strict JSON validation.
    Falls back to labeled mock if ANTHROPIC_API_KEY is not configured or on API error.
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.info("ANTHROPIC_API_KEY not set; using labeled mock OCR extractor")
        return mock_ocr_extract_card()

    prompt = """You are an OCR specialist extracting values from an official Government of India Soil Health Card (मृदा स्वास्थ्य कार्ड).
Extract all present numeric parameters into a strict JSON object with these exact keys:
- ph: float (soil pH, 3.0 to 11.0)
- ec: float (electrical conductivity in dS/m)
- oc: float (organic carbon in %)
- n: float (available nitrogen in kg/ha)
- p: float (available phosphorus in kg/ha)
- k: float (available potassium in kg/ha)
- sulphur: float (ppm or kg/ha, or null)
- zinc: float (ppm, or null)
- iron: float (ppm, or null)
- copper: float (ppm, or null)
- manganese: float (ppm, or null)
- boron: float (ppm, or null)

Output ONLY valid JSON without markdown fences, explanations, or commentary."""

    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("x-api-key", settings.ANTHROPIC_API_KEY)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content_blocks = data.get("content", [])
            raw_text = content_blocks[0].get("text", "{}") if content_blocks else "{}"
            # Clean possible markdown wrap
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0]
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0]
            parsed = json.loads(raw_text.strip())
            validated = validate_soil_card_ranges(parsed)
            return {
                "is_mock_ocr": False,
                "engine": f"Claude Vision ({settings.ANTHROPIC_MODEL})",
                "extracted_values": validated,
                "needs_confirmation": True,
                "notice": "Please verify and adjust the extracted numbers before saving."
            }
    except Exception as e:
        logger.error(f"Claude Vision OCR failed: {e}. Falling back to mock extractor.")
        fallback = mock_ocr_extract_card()
        fallback["notice"] = f"Vision API error ({e}). Displaying mock values for confirmation."
        return fallback


def mock_ocr_extract_card() -> Dict[str, Any]:
    """Fallback simulated OCR extraction for development / testing."""
    return {
        "is_mock_ocr": True,
        "engine": "Simulated OCR Stub",
        "extracted_values": {
            "ph": 7.4,
            "ec": 0.42,
            "oc": 0.58,
            "n": 240.0,
            "p": 16.5,
            "k": 310.0,
            "sulphur": 12.0,
            "zinc": 0.65,
            "iron": 4.8,
            "copper": 0.32,
            "manganese": 3.1,
            "boron": 0.45
        },
        "needs_confirmation": True,
        "notice": "Simulated OCR data. Please verify each parameter against your physical Soil Health Card."
    }
