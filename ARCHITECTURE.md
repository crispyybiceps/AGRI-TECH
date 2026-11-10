# AGRI-TECH: System Architecture & Data Flow

## 1. System Philosophy & Target User Context
AGRI-TECH is built specifically for Indian smallholder farmers (starting with Maharashtra) characterized by:
- Low digital literacy: oversized touch targets, simple icon cards, minimal typing required.
- Basic Android hardware: lightweight PWA assets (<500 KB JS bundle), standalone home-screen launch.
- Intermittent 2G/3G connectivity: local SQLite caching (3-hour weather refresh), offline fallback data.
- Multilingual priority: immediate one-tap switching between Marathi (`मराठी`), Hindi (`हिंदी`), and English (`en`), paired with Web Speech API for bidirectional voice interaction (Speech-To-Text and Text-To-Speech).

---

## 2. Architecture Diagram

```
+--------------------------------------------------------------------------+
|                       FRONTEND: React 19 + Vite PWA                      |
|                                                                          |
|  [Language Switcher]  [Web Speech STT/TTS]  [PWA Service Worker Cache]    |
|                                                                          |
|     +-------------+    +-------------+    +-------------+   +----------+ |
|     |  Ask Expert |    |   Weather   |    |   My Soil   |   |   Sell   | |
|     | (AI Chatbot)|    |  (Advisory) |    |  (Tiered)   |   | (Prices) | |
|     +-------------+    +-------------+    +-------------+   +----------+ |
+------------------------------------+-------------------------------------+
                                     |  HTTP / JSON (Axios + JWT Bearer)
                                     v
+------------------------------------+-------------------------------------+
|                     BACKEND: FastAPI + Python 3.13                       |
|                                                                          |
|  [JWT Auth & Mock OTP]     [CORS Middleware]     [User Isolation Layer]  |
|                                                                          |
|  +--------------------+  +--------------------+  +--------------------+  |
|  |   Weather Router   |  |    Soil Router     |  |    Chat Router     |  |
|  |  - 3hr SQLite Cache|  |  - Tier 1: Lab SHC |  |  - BM25 RAG Engine |  |
|  |  - Advisory Engine |  |  - Tier 2: Grids   |  |  - Tool Calling    |  |
|  |  - Crop Calendar   |  |  - Tier 3: Visual  |  |  - Safety Filter   |  |
|  +--------------------+  +--------------------+  +--------------------+  |
|                                                                          |
|  +--------------------+  +--------------------+  +--------------------+  |
|  | Marketplace Router |  |    Admin Router    |  |   External APIs    |  |
|  |  - Price Compare   |  |  - QA Review Queue |  |  - Open-Meteo      |  |
|  |  - Listings CRUD   |  |  - Buyer Verify    |  |  - ISRIC SoilGrids |  |
|  |  - Offer Lifecycle |  |  - KB Doc Editor   |  |  - Anthropic Claude|  |
|  +--------------------+  +--------------------+  +--------------------+  |
+------------------------------------+-------------------------------------+
                                     |  SQLAlchemy ORM
                                     v
+------------------------------------+-------------------------------------+
|                       DATABASE: SQLite (agritech.db)                     |
|                                                                          |
|   Users  |  OTPs  |  Farms  |  WeatherCache  |  SoilRecords  |  Sensors  |
|        ChatSessions  |  ChatMessages  |  Listings  |  Offers  |  Prices  |
+--------------------------------------------------------------------------+
```

---

## 3. Data Flow Pipelines

### A. Weather Advisory Pipeline
1. Client requests `GET /weather/{farm_id}`.
2. Backend checks `weather_cache` table. If cached forecast is `< 3 hours` old, returns instantly with `cached: true`.
3. If cache has expired, queries Open-Meteo API (or uses labeled `# MOCK:` fallback if offline).
4. Advisory engine evaluates rainfall (>20mm = delay spray), wind speed (>20 km/h = drift alert), and temperature (>36°C = heatwave).
5. Responses translated into Marathi, Hindi, and English.
6. Client Web Speech API speaks the advisory aloud upon tapping "Read aloud" / "ऐका".

### B. Tiered Soil Insight Pipeline
1. **Tier 1 (High)**: Lab Soil Health Card entered or pre-populated via simulated OCR stub. Evaluates pH, EC, OC, N, P, K against Indian agricultural standards (`soil_standards.json`) and generates lime/gypsum/FYM amendment requirements.
2. **Tier 2 (Low/Med)**: ISRIC SoilGrids geographic query for regional basalt/Vertisol profile, always tagged as an *ESTIMATE, not a lab test*.
3. **Tier 3 (Low)**: 5-question visual field observation. Evaluates indications using "Possible indication of...", never "diagnosis".
4. Storage: Persists in `soil_records`. When querying `/soil/{farm_id}`, the highest confidence record is always prioritized first.

### C. AI Chatbot RAG & Safety Pipeline
1. Farmer query received (via typing or Web Speech microphone).
2. Intent classifier triggers tools if needed:
   - Queries `get_weather(farm_id)` if spray/rain/wind mentioned.
   - Queries `get_soil_insights(farm_id)` if soil/fertilizer mentioned.
   - Queries `get_market_prices(crop)` if prices/mandi mentioned.
3. BM25 algorithm retrieves top relevant chunks from `/knowledge` markdown files.
4. **Safety Filter**:
   - Intercepts banned chemicals (Monocrotophos, Endosulfan, Paraquat) and issues mandatory toxicity warnings.
   - Requires CIB&RC documentation for chemical recommendations; refers to KVK if unverified.
   - Mandates protective gear (PPE), pre-harvest interval (PHI), and child safety reminders on every pesticide response.
5. Invokes LLM (Claude via Anthropic API) or fallback expert engine.
6. Messages stored in `chat_messages` with citation sources. Farmers can flag any message for KVK administrative QA review.

### D. Marketplace & Middleman Disintermediation Pipeline
1. Farmer inputs crop, quantity, quality grade, and expected price.
2. System compares expected price to prevailing Mandi APMC modal rates, returning instant visual feedback (`below`, `fair`, `above`).
3. Registered buyers browse active listings with verified trust badges.
4. Offer Lifecycle:
   `listed` ➔ `offer_made` (buyer submits bid) ➔ `confirmed` (farmer accepts) ➔ `delivered` (produce handed over).

