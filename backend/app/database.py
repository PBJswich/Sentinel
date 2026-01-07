"""
Database connection and session management.

Supports SQLite (default) and PostgreSQL (optional for production).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Determine database type from environment
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"
POSTGRES_URL = os.getenv("DATABASE_URL")  # e.g., postgresql://user:pass@host:port/dbname

if USE_POSTGRES and POSTGRES_URL:
    # PostgreSQL configuration
    DATABASE_URL = POSTGRES_URL
    connect_args = {}
else:
    # SQLite configuration (default)
    BASE_DIR = Path(__file__).parent.parent.parent
    DATABASE_URL = f"sqlite:///{BASE_DIR / 'data' / 'sentinel.db'}"
    connect_args = {"check_same_thread": False}  # Needed for SQLite

# Create engine with appropriate configuration
if USE_POSTGRES:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        echo=False,  # Set to True for SQL query logging
        pool_pre_ping=True,  # Reconnect if connection lost
        pool_size=10,  # Connection pool size
        max_overflow=20  # Max overflow connections
    )
else:
    # SQLite configuration (no connection pooling)
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        echo=False  # Set to True for SQL query logging
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

