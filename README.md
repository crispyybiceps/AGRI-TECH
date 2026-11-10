# AGRI-TECH 🌾

A **mobile-first Progressive Web App (PWA)** for Indian farmers (starting with Maharashtra). Designed for users with low digital literacy and slow internet: big icons, minimal typing, voice-friendly, with full **Marathi / Hindi / English** support.

---

## Features

| Module | Description |
|---|---|
| **Auth & Profile** | Phone-number OTP login (mock SMS, prints to console). JWT tokens. Profile with name & language preference. |
| **Farm Management** | Full CRUD for farms: name, village, lat/lng, size in acres, crops. Scoped to authenticated user. |
| **Weather & Advisory** | 7-day forecast via Open-Meteo (no API key needed). 3-hour SQLite cache. Rule-based advisory in 3 languages. Seasonal crop/seed suggestions. "Read aloud" via Web Speech API. |
| **Soil Module (Tiered)** | Tier 1: Lab Soil Health Card entry + interpretation. Tier 2: SoilGrids satellite estimate (labeled ESTIMATE). Tier 3: Visual field observation. Tier 4: IoT sensor stub. Tier 5: Lab directory & sampling guide. |
| **AI Chatbot** | RAG over verified knowledge base (pesticides, crops, fertilizer, schemes). Tool calling for weather, soil, market data. Safety guardrails (banned pesticide warnings, PPE, KVK referral). Voice input & TTS. Rule-based fallback when no API key is set. |
| **Marketplace & Mandi Prices** | Direct farmer-to-buyer listings. Mock Agmarknet APMC price comparison. Buyer offer lifecycle (offer → confirm → deliver). |
| **Admin Panel** | Analytics dashboard. Flagged chatbot answer review. Buyer verification. Knowledge base editor with RAG re-index. |
| **PWA** | `manifest.json`, service worker, installable on Android home screen. |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite, Tailwind CSS v4, react-i18next, Web Speech API |
| Backend | Python FastAPI, SQLAlchemy, SQLite |
| Auth | Phone OTP (mock) + JWT |
| Weather | Open-Meteo API (free, no key) |
| AI Chatbot | Claude via Anthropic API (optional; rule-based fallback if no key) |
| i18n | Marathi (`mr`), Hindi (`hi`), English (`en`) |

---

## Project Structure

```
AGRI-TECH/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── models.py            # All SQLAlchemy models
│   │   ├── database.py          # DB engine & session
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── auth.py              # JWT creation & verification
│   │   ├── routers/
│   │   │   ├── auth_router.py
│   │   │   ├── profile_router.py
│   │   │   ├── farm_router.py
│   │   │   ├── weather_router.py
│   │   │   ├── soil_router.py   # Also exports sensor_router
│   │   │   ├── chat_router.py
│   │   │   ├── marketplace_router.py
│   │   │   └── admin_router.py
│   │   ├── services/
│   │   │   ├── weather_service.py
│   │   │   ├── soil_service.py
│   │   │   ├── chatbot_service.py
│   │   │   ├── rag_service.py
│   │   │   └── mandi_service.py
│   │   ├── knowledge/           # RAG knowledge base (markdown files)
│   │   └── data/
│   │       ├── crop_calendar.json
│   │       ├── soil_standards.json
│   │       └── maharashtra_soil_labs.json
│   ├── seed.py                  # Demo data seeder
│   ├── requirements.txt
│   ├── .env / .env.example
│   └── venv/
├── frontend/
│   ├── src/
│   │   ├── pages/               # Login, Home, Profile, FarmForm, FarmList,
│   │   │                        # WeatherPage, SoilPage, ChatPage,
│   │   │                        # MarketplacePage, AdminPage
│   │   ├── components/          # BottomNav, LanguageSwitcher
│   │   ├── locales/             # en.json, hi.json, mr.json
│   │   ├── services/            # api.js (Axios + JWT interceptor)
│   │   └── main.jsx
│   ├── public/
│   │   ├── manifest.json
│   │   ├── sw.js
│   │   ├── icon-192.png
│   │   └── icon-512.png
│   └── package.json
├── PROGRESS.md
├── API_DOCUMENTATION.md
├── ARCHITECTURE.md
├── LIMITATIONS_AND_FUTURE_WORK.md
├── DEMO_SCRIPT.md
└── .gitignore
```

---

## Quick Start

### Prerequisites
- **Python 3.13+** (with pip)
- **Node.js 18+** (with npm)

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY for production
# Optional: add ANTHROPIC_API_KEY for Claude-powered chatbot

# Seed demo data (optional)
python seed.py

# Start the server
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

- App: http://localhost:5173

### Test Login

1. Open the app at http://localhost:5173
2. Enter any 10-digit phone number (e.g., `9876543210`)
3. Check the **backend terminal** for `[MOCK OTP: 123456]`
4. Enter the OTP → you're logged in with a JWT

---

## API Documentation

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for all endpoints with sample requests and responses.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design, data flow, and component diagrams.

## Limitations & Future Work

See [LIMITATIONS_AND_FUTURE_WORK.md](LIMITATIONS_AND_FUTURE_WORK.md) for honest assessment of what is real vs. mocked, soil testing accuracy limits, and pilot recommendations.

## Demo Walkthrough

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for a step-by-step farmer journey with API examples.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | JWT signing key (change in production) |
| `DATABASE_URL` | Yes | SQLite connection string (default: `sqlite:///./agritech.db`) |
| `OTP_EXPIRY_MINUTES` | No | OTP validity period (default: 5) |
| `ACCESS_TOKEN_EXPIRE_DAYS` | No | JWT token lifetime (default: 7) |
| `ANTHROPIC_API_KEY` | No | Enables Claude-powered chatbot. Without it, uses rule-based fallback (labeled MOCK). |

---

## License

This project is for educational and demonstration purposes.
