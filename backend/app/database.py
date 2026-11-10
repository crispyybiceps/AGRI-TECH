"""
Database setup module for AGRI-TECH.
Supports both Supabase PostgreSQL and SQLite.
Removes SQLite-only settings when connecting to Postgres.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

db_url = settings.DATABASE_URL

# SQLite requires check_same_thread=False; Postgres pool settings are standard
engine_kwargs = {}
if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Postgres configuration (pool size, pre-ping for connection health)
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modern SQLAlchemy 2.0 declarative_base
Base = declarative_base()


def get_db():
    """
    Dependency that provides a database session per request.
    Ensures the session is closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
