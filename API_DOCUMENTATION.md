# AGRI-TECH: Complete REST API Documentation

Base URL: `http://localhost:8000`  
Interactive Swagger UI: `http://localhost:8000/docs`  
ReDoc UI: `http://localhost:8000/redoc`

All authenticated endpoints require an `Authorization: Bearer <JWT_ACCESS_TOKEN>` header.

---

## 1. Authentication (`/auth`)

### `POST /auth/send-otp`
Generates a 6-digit mock OTP and prints it to the backend console. Automatically registers the user if the phone number is new.

**Request:**
```json
{
  "phone": "+919876543210"
}
```

**Response (200 OK):**
```json
{
  "message": "OTP sent",
  "phone": "+919876543210"
}
```
*Console output:* `[MOCK OTP] Phone: +919876543210 | OTP: 821937`

---

### `POST /auth/verify-otp`
Validates the OTP and returns a signed 7-day JWT access token.

**Request:**
```json
{
  "phone": "+919876543210",
  "otp": "821937"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "phone": "+919876543210",
    "name": "Ramesh Patil"
  }
}
```

---

## 2. Farmer Profile (`/profile`)

### `GET /profile`
Retrieves the logged-in farmer's profile.

**Response (200 OK):**
```json
{
  "id": 1,
  "phone": "+919876543210",
  "name": "Ramesh Patil",
  "language_preference": "mr",
  "created_at": "2026-11-10T12:00:00",
  "updated_at": "2026-11-10T12:00:00"
}
```

### `PUT /profile`
Updates farmer profile fields.

**Request:**
```json
{
  "name": "Ramesh Patil (सुधारित नाव)",
  "language_preference": "mr"
}
```

---

## 3. Farm Plots (`/farms`)

### `POST /farms` (Status: 201 Created)
```json
{
  "name": "Shree Ganesh Farm",
  "village": "Baramati",
  "latitude": 18.1512,
  "longitude": 74.5789,
  "size_acres": 4.5,
  "crops": "Sugarcane, Soybean"
}
```

### `GET /farms`
Returns all farms owned by the logged-in user.

### `GET /farms/{farm_id}`
Returns a single farm plot. Returns `403 Forbidden` if accessed by another farmer.

---

## 4. Weather & Advisory (`/weather`, `/advisory`)

### `GET /weather/{farm_id}`
Returns 7-day forecast from Open-Meteo API or SQLite cache (refreshed every 3 hours).

**Sample Response:**
```json
{
  "farm_id": 1,
  "farm_name": "Shree Ganesh Farm",
  "cached": true,
  "cached_at": "2026-11-10T12:00:00",
  "current": {
    "temperature_2m": 29.5,
    "relative_humidity_2m": 62,
    "wind_speed_10m": 12.5,
    "weather_code": 1
  },
  "daily": {
    "time": ["2026-11-10", "2026-11-11", "2026-11-12"],
    "temperature_2m_max": [33.5, 34.0, 31.5],
    "temperature_2m_min": [21.0, 21.5, 22.0],
    "precipitation_probability_max": [10, 35, 75],
    "precipitation_sum": [0.0, 1.2, 14.5]
  }
}
```

### `GET /advisory/{farm_id}`
Generates rule-based agricultural advisories in Marathi, Hindi, and English based on the weather forecast and standing crops.

---

## 5. Tiered Soil Module (`/soil`)

### `POST /soil/card/{farm_id}` (Tier 1 - High Confidence)
```json
{
  "ph": 7.4,
  "ec": 0.42,
  "oc": 0.65,
  "n": 290.0,
  "p": 22.0,
  "k": 240.0,
  "crop": "Sugarcane"
}
```

### `POST /soil/ocr-stub`
Returns simulated OCR-extracted values from photo of a Government Soil Health Card.

### `POST /soil/observation/{farm_id}` (Tier 3 - Low Confidence)
```json
{
  "color": "black_dark",
  "texture": "clay_sticky",
  "drainage": "moderate_24h",
  "cracking": "deep_cracks",
  "symptom": "yellow_lower_leaves"
}
```

### `GET /soil/soilgrids/{farm_id}` (Tier 2 - Low/Medium Confidence)
Queries ISRIC SoilGrids 250m model. Always flagged with: `"ESTIMATE, not a lab test"`.

### `GET /soil/{farm_id}`
Retrieves the highest-confidence soil record (Tier 1 > Tier 2 > Tier 3) and historical test log.

### `GET /soil/labs` (Tier 5)
Returns sample collection steps and directory of Maharashtra accredited testing labs/KVKs.

---

## 6. Multilingual AI Chatbot (`/chat`)

### `POST /chat`
```json
{
  "message": "Is it safe to spray pesticides today?",
  "farm_id": 1,
  "language": "mr"
}
```
**Sample Response:**
```json
{
  "session_id": 1,
  "message_id": 4,
  "reply": "☀️ आज फवारणीसाठी हवामान अनुकूल आहे. वाऱ्याचा वेग शांत असून पाऊस नाही...",
  "sources": ["cibrc_pesticides_and_ipm.md"],
  "tools_used": ["get_weather"]
}
```

### `POST /chat/messages/{message_id}/flag`
Allows farmer to flag an answer for agricultural specialist QA review.

---

## 7. Marketplace & Prices (`/marketplace`)

### `GET /marketplace/prices`
Lists reference Mandi APMC prices (Agmarknet simulated/real dataset) across Maharashtra.

### `POST /marketplace/compare-price`
```json
{
  "crop": "Soybean",
  "expected_price": 4700.0
}
```
**Response:**
```json
{
  "indicator": "fair",
  "mandi_modal": 4650.0,
  "diff_percentage": 1.1,
  "advice_en": "Fair market price! Your price aligns closely with Mandi modal average."
}
```

### `POST /marketplace/listings`
Creates a direct harvest listing for buyers.

### `POST /marketplace/listings/{id}/offer`
Buyer submits a price offer on a listing.

### `PUT /marketplace/offers/{id}/status`
Progresses offer lifecycle: `offer_made` ➔ `confirmed` ➔ `delivered`.

---

## 8. Admin Oversight (`/admin`)

- `GET /admin/analytics`: Platform analytics (users, listings, chats, flagged QAs).
- `PUT /admin/verify-buyer/{user_id}`: Assigns or revokes verified buyer trust badge.
- `GET /admin/knowledge`: Lists RAG knowledge base markdown documents.
- `PUT /admin/knowledge/{filename}`: Edits document and triggers immediate RAG re-index.

