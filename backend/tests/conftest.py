"""
Pytest configuration for AGRI-TECH tests.
Ensures ALL tests run against an isolated SQLite test database
and NEVER touch the remote Supabase PostgreSQL database.
"""

import os
import sys

# Ensure test DB is set BEFORE any app module imports
TEST_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_isolated.db"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"
os.environ["TESTING"] = "true"

import pytest
from fastapi.testclient import TestClient
from app.database import Base, get_db, SessionLocal, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_engine():
    """Initializes tables in isolated SQLite database for testing."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
