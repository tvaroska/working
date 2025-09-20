"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from .config import get_settings

settings = get_settings()

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Session:
    """
    FastAPI dependency to get database session.
    
    Creates a new database session for each request and ensures proper
    cleanup after the request is completed. Uses dependency injection
    pattern to provide database access to API endpoints.
    
    Yields:
        Session: SQLAlchemy database session for the request
        
    Note:
        Session is automatically closed after request completion
        to prevent connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables defined in the models.
    
    Uses SQLAlchemy's metadata to create all tables that are defined
    in the application models. This is typically called during
    application initialization or database migrations.
    
    Note:
        Only creates tables that don't already exist. Existing
        tables are left unchanged.
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables defined in the models.
    
    Uses SQLAlchemy's metadata to drop all tables that are defined
    in the application models. This is typically used for testing
    or during development for clean database resets.
    
    Warning:
        This will permanently delete all data in the tables.
        Use with extreme caution in production environments.
    """
    Base.metadata.drop_all(bind=engine)