"""
core/database.py
────────────────
SQLAlchemy engine, session factory, and declarative base.
All ORM models import `Base` from here.
All routes/services get a DB session via `get_db()` dependency.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from core.config import settings


# ── Engine ──────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    echo=(settings.APP_ENV == "development"),  # Log SQL in dev only
    pool_pre_ping=True,                         # Reconnect if connection dropped
    pool_size=5,
    max_overflow=10,
)

# ── Session Factory ──────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Declarative Base ─────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this class."""
    pass


# ── FastAPI Dependency ───────────────────────────────────
def get_db():
    """
    Yields a database session for use in FastAPI route dependencies.

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
