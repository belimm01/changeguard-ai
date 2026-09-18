"""Plumbing helpers for real-Postgres repository tests.

Not a test module. Provides a fresh, isolated AsyncSession backed by the
disposable Postgres, so each test starts from an empty schema. Tests drive
the returned async context manager with ``asyncio.run`` to match the
project's async-test convention (no pytest-asyncio dependency).
"""

import os
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from changeguard.db import models as _models  # noqa: F401  (register tables on Base)
from changeguard.db.base import Base

DB_URL = os.environ.get(
    "CHANGEGUARD_TEST_DB_URL",
    "postgresql+asyncpg://cg:cg@localhost:55432/changeguard",
)


def postgres_available() -> bool:
    """True if the configured Postgres accepts a TCP connection quickly."""
    url = make_url(DB_URL)
    try:
        with socket.create_connection((url.host or "localhost", url.port or 5432), 0.5):
            return True
    except OSError:
        return False


@asynccontextmanager
async def fresh_session() -> AsyncIterator[AsyncSession]:
    """Drop/recreate all tables, then yield one session on an empty schema."""
    engine = create_async_engine(DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
