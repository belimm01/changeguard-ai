"""SQLAlchemy declarative base and shared metadata."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base carrying the shared metadata for all models."""
