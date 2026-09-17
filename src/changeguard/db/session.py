"""Async engine and session factory helpers."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from changeguard.config import DatabaseSettings


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Create an async engine from database settings without logging credentials."""
    return create_async_engine(
        settings.url.get_secret_value(),
        echo=False,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory that does not auto-expire committed instances."""
    return async_sessionmaker(engine, expire_on_commit=False)
