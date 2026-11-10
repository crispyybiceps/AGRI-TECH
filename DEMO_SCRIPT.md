# AGRI-TECH: Demo Script — One Farmer Journey

This walkthrough demonstrates the complete AGRI-TECH experience using API calls (`curl`) against `http://localhost:8000`. You can also follow along in the Swagger UI at `/docs`.

> **Prerequisites**: Backend running on port 8000, frontend on port 5173. Optionally run `python seed.py` first for pre-loaded demo data.

---

## 1. Login with Mock OTP

### Send OTP
```bash
curl -X POST http://localhost:8000/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "9876543210"}'
```
**Response**: `{"message": "OTP sent successfully", "phone": "9876543210"}`  
**Check backend terminal**: You'll see `[MOCK OTP: 123456]` printed.

### Verify OTP and Get JWT
```bash
curl -X POST http://localhost:8000/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "9876543210", "otp": "123456"}'
```
**Response**: `{"access_token": "eyJ...", "token_type": "bearer"}`

> Save the token for all subsequent requests:
> ```bash
> TOKEN="eyJ..."
> ```

---

## 2. Complete Profile

```bash
curl -X PUT http://localhost:8000/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Ramesh Patil", "language_preference": "mr"}'
```

---

## 3. Create a Farm with Location

```bash
curl -X POST http://localhost:8000/farms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "North Field",
    "village": "Phaltan, Satara",
    "latitude": 17.9922,
    "longitude": 74.4330,
    "size_acres": 3.5,
    "crops": "soybean,jowar"
  }'
```
**Response** includes the new `farm_id` (e.g., `1`).

---

## 4. Check Weather Forecast and Advisory

### 7-Day Forecast
```bash
curl http://localhost:8000/weather/1 \
  -H "Authorization: Bearer $TOKEN"
```
Returns daily forecast with temperature, rain probability, humidity, wind. Cached for 3 hours.

### Agricultural Advisory
```bash
curl http://localhost:8000/advisory/1 \
  -H "Authorization: Bearer $TOKEN"
```
Returns plain-language advice like:
- "Heavy rain expected — delay spraying and sowing"
- "Dry spell — irrigate early morning"
- Seasonal crop suggestions from `crop_calendar.json`

---

## 5. Enter Soil Health Card Data

```bash
curl -X POST http://localhost:8000/soil/card/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ph": 6.8,
    "ec": 0.35,
    "organic_carbon": 0.55,
    "nitrogen": 210,
    "phosphorus": 18,
    "potassium": 280
  }'
```
Returns Tier 1 (High confidence) interpretation with fertilizer/amendment advice.

### Visual Field Observation (Tier 3)
```bash
curl -X POST http://localhost:8000/soil/observation/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "soil_color": "dark_brown",
    "texture": "clayey",
    "drainage": "slow",
    "cracking": "yes",
    "leaf_symptoms": "yellowing"
  }'
```
Returns Low confidence estimate with prominent disclaimer: "Possible indication of…"

### Find Nearest Lab
```bash
curl http://localhost:8000/soil/labs \
  -H "Authorization: Bearer $TOKEN"
```

---

## 6. Ask the Chatbot — Safe Query

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Is it safe to spray today?",
    "farm_id": 1,
    "language": "en"
  }'
```
The chatbot calls `get_weather(farm_id=1)` internally, checks wind speed and rain, and responds with safety advice. If it's rainy/windy: **"NO — delay spraying."** With PPE reminders.

---

## 7. Ask About a Banned Pesticide (Safety Test)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can I use Monocrotophos on my brinjal?",
    "farm_id": 1,
    "language": "en"
  }'
```
**Expected**: The chatbot MUST refuse and warn:
- ⚠️ **BANNED** — Monocrotophos is banned by CIB&RC
- Recommends safer alternatives (Chlorantraniliprole, Neem oil)
- Includes PPE and child safety warnings

---

## 8. List Produce on Marketplace

```bash
curl -X POST http://localhost:8000/marketplace/listings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "crop": "Soybean",
    "quantity_quintals": 15.0,
    "quality_grade": "Grade A (Premium)",
    "expected_price": 5200,
    "location": "Phaltan, Satara"
  }'
```

### Compare with Mandi Price
```bash
curl -X POST http://localhost:8000/marketplace/compare-price \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"crop": "Soybean", "expected_price": 5200}'
```
Returns `fair`, `below`, or `above` with the current Mandi modal rate.

---

## 9. Buyer Makes an Offer

### Register as Buyer (new phone)
```bash
# First send OTP and login with a different phone
curl -X POST http://localhost:8000/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "9988776655"}'

curl -X POST http://localhost:8000/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "9988776655", "otp": "123456"}'
# Save as BUYER_TOKEN

curl -X POST http://localhost:8000/marketplace/register-buyer \
  -H "Authorization: Bearer $BUYER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"business_name": "Satara Agri Traders"}'
```

### Browse Listings and Make Offer
```bash
curl http://localhost:8000/marketplace/listings \
  -H "Authorization: Bearer $BUYER_TOKEN"

# Offer on listing ID 1
curl -X POST http://localhost:8000/marketplace/listings/1/offer \
  -H "Authorization: Bearer $BUYER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "offered_price": 5100,
    "quantity": 10,
    "buyer_notes": "Can pick up from farm gate"
  }'
```

### Farmer Confirms and Delivers
```bash
# Farmer checks offers
curl http://localhost:8000/marketplace/offers \
  -H "Authorization: Bearer $TOKEN"

# Farmer confirms (offer_id = 1)
curl -X PUT http://localhost:8000/marketplace/offers/1/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}'

# After delivery
curl -X PUT http://localhost:8000/marketplace/offers/1/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "delivered"}'
```

---

## 10. Admin Panel

Use an admin account (seeded by `seed.py` with phone `9999999999`):

```bash
# Login as admin
curl -X POST http://localhost:8000/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "9999999999"}'

curl -X POST http://localhost:8000/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "9999999999", "otp": "123456"}'
# Save as ADMIN_TOKEN

# View analytics
curl http://localhost:8000/admin/analytics \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# View flagged chatbot answers
curl http://localhost:8000/chat/flagged \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Verify a buyer
curl -X POST http://localhost:8000/admin/verify-buyer/2 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## UI Walkthrough (Frontend)

1. Open http://localhost:5173
2. **Login**: Enter phone → see OTP in backend terminal → enter it → landed on Home
3. **Language**: Tap the 🌐 switcher in the header → switch to मराठी or हिंदी — all text updates instantly
4. **Home Screen**: 4 big buttons — Ask Expert, Weather, My Soil, Sell/Prices
5. **Weather**: Tap Weather → see 7-day forecast with icons → tap "Read aloud 🔊" to hear it spoken
6. **Farm**: Navigate to farm list → Add Farm → fill in details → "Use My Location" for GPS
7. **Soil**: Tap My Soil → Enter Soil Health Card values OR record Visual Observation → see color-coded results
8. **Chat**: Tap Ask Expert → type or use 🎤 voice → see response with source citations → tap 🔊 to hear it → tap 🚩 to flag bad advice
9. **Marketplace**: Tap Sell/Prices → browse Mandi rates → Create listing → see price comparison pill
10. **Admin**: Login with admin phone → see analytics, flagged QA queue, buyer verification

