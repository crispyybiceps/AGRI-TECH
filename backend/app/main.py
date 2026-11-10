"""
AGRI-TECH Backend — Main Application Entry Point

A mobile-first web API for Indian farmers, providing:
- Phone-based OTP authentication
- User profile management
- Farm CRUD operations

Run with: uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import (
    auth_router,
    profile_router,
    farm_router,
    weather_router,
    soil_router,
    chat_router,
    marketplace_router,
    admin_router,
)

# ──────────────────────────────────────────────
# Create all database tables on startup
# ──────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ──────────────────────────────────────────────
# Initialize FastAPI application
# ──────────────────────────────────────────────
app = FastAPI(
    title="AGRI-TECH API",
    description="Backend API for the AGRI-TECH mobile-first web app for Indian farmers",
    version="1.0.0",
)

# ──────────────────────────────────────────────
# CORS Middleware — allow all origins for development
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],          # Allow all HTTP methods
    allow_headers=["*"],          # Allow all headers
)

# ──────────────────────────────────────────────
# Register Routers
# ──────────────────────────────────────────────
app.include_router(auth_router.router)       # /auth/*
app.include_router(profile_router.router)    # /profile
app.include_router(farm_router.router)       # /farms/*
app.include_router(weather_router.router)    # /weather/*, /advisory/*
app.include_router(soil_router.router)       # /soil/*
app.include_router(soil_router.sensor_router) # /sensors/*
app.include_router(chat_router.router)       # /chat/*
app.include_router(marketplace_router.router) # /marketplace/*
app.include_router(admin_router.router)       # /admin/*


# ──────────────────────────────────────────────
# Health Check Endpoint
# ──────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health_check():
    """Root endpoint — confirms the API is running."""
    return {
        "status": "healthy",
        "app": "AGRI-TECH API",
        "version": "1.0.0",
    }
