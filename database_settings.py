"""
Database settings for the Password Manager application.

This module configures the SQLAlchemy engine, session, and base class
for ORM models. It uses a local SQLite database file named 'passwords.db'.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database connection URL (SQLite file-based database)
SQLALCHEMY_DATABASE_URL = f"sqlite:///./passwords.db"

# Create SQLAlchemy engine with SQLite-specific connection arguments
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a configured "Session" class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()
