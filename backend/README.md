# AGRI-TECH Backend

A FastAPI backend for the AGRI-TECH mobile-first web application designed for Indian farmers.

## Features

- **Phone-based OTP Authentication** — Mock OTP for development (printed to console)
- **User Profile Management** — View and update farmer profiles
- **Farm CRUD** — Create, read, update, and delete farm records
- **JWT Authorization** — Secure API access with 7-day tokens
- **SQLite Database** — Lightweight, zero-config file-based storage

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work for development)
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### 4. API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint              | Auth | Description               |
|--------|-----------------------|------|---------------------------|
| GET    | `/`                   | No   | Health check              |
| POST   | `/auth/send-otp`      | No   | Send mock OTP             |
| POST   | `/auth/verify-otp`    | No   | Verify OTP, get JWT       |
| GET    | `/profile`            | JWT  | Get user profile          |
| PUT    | `/profile`            | JWT  | Update user profile       |
| POST   | `/farms`              | JWT  | Create a new farm         |
| GET    | `/farms`              | JWT  | List user's farms         |
| GET    | `/farms/{farm_id}`    | JWT  | Get a specific farm       |
| PUT    | `/farms/{farm_id}`    | JWT  | Update a farm             |
| DELETE | `/farms/{farm_id}`    | JWT  | Delete a farm             |

## Auth Flow (Development)

1. Call `POST /auth/send-otp` with `{"phone": "9876543210"}`
2. Check the server console for the `[MOCK OTP]` message
3. Call `POST /auth/verify-otp` with `{"phone": "9876543210", "otp": "<otp-from-console>"}`
4. Use the returned `access_token` in the `Authorization: Bearer <token>` header for protected endpoints

## Project Structure

```
backend/
├── app/
│   ├── __init__.py          # Package init
│   ├── main.py              # FastAPI app, CORS, routers
│   ├── config.py            # Settings from .env
│   ├── database.py          # SQLite + SQLAlchemy setup
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── auth.py              # JWT token creation/verification
│   ├── dependencies.py      # FastAPI dependencies (get_current_user)
│   └── routers/
│       ├── __init__.py      # Package init
│       ├── auth_router.py   # OTP send/verify endpoints
│       ├── profile_router.py# Profile GET/PUT endpoints
│       └── farm_router.py   # Farm CRUD endpoints
├── .env.example             # Environment variable template
├── .env                     # Local environment config (not committed)
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Tech Stack

- **FastAPI** — High-performance async web framework
- **SQLAlchemy** — ORM for database operations
- **SQLite** — File-based database (no server needed)
- **python-jose** — JWT token handling
- **Pydantic** — Data validation and serialization
- **Uvicorn** — ASGI server
