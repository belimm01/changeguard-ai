"""Exercise versioned schema creation and rollback against disposable PostgreSQL."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from integration.db._db import DB_URL, postgres_available

pytestmark = pytest.mark.skipif(
    not postgres_available(), reason="Postgres is not available"
)


def _table_names(connection: Connection) -> list[str]:
    return inspect(connection).get_table_names(schema="public")


def _assert_job_schema(connection: Connection) -> None:
    assert "analysis_jobs" in _table_names(connection)
    inspector = inspect(connection)
    columns = {
        column["name"]: column for column in inspector.get_columns("analysis_jobs")
    }
    assert set(columns) == {
        "id",
        "repository_owner",
        "repository_name",
        "pull_request_number",
        "base_sha",
        "head_sha",
        "analysis_version",
        "state",
        "requested_at",
        "completed_at",
        "report_json",
        "failure_reason",
        "lease_owner",
        "lease_expires_at",
    }
    assert columns["requested_at"]["default"] is not None
    assert not columns["state"]["nullable"]
    assert columns["lease_owner"]["nullable"]
    assert columns["lease_expires_at"]["nullable"]
    constraints = inspector.get_unique_constraints("analysis_jobs")
    identity = next(
        item for item in constraints if item["name"] == "uq_analysis_jobs_identity"
    )
    assert identity["column_names"] == [
        "repository_owner",
        "repository_name",
        "pull_request_number",
        "base_sha",
        "head_sha",
        "analysis_version",
    ]
    assert inspector.get_pk_constraint("analysis_jobs")["constrained_columns"] == ["id"]
    states = (
        connection.execute(
            text(
                "SELECT e.enumlabel FROM pg_enum e "
                "JOIN pg_type t ON t.oid = e.enumtypid "
                "JOIN pg_namespace n ON n.oid = t.typnamespace "
                "WHERE t.typname = 'job_state' AND n.nspname = 'public'"
            )
        )
        .scalars()
        .all()
    )
    assert set(states) == {"queued", "running", "completed", "partial", "failed"}


async def _reset_database() -> None:
    engine = create_async_engine(DB_URL)
    try:
        async with engine.begin() as connection:
            for statement in (
                "DROP TABLE IF EXISTS analysis_jobs",
                "DROP TYPE IF EXISTS job_state",
                "DROP TABLE IF EXISTS alembic_version",
            ):
                await connection.execute(text(statement))
            assert "analysis_jobs" not in await connection.run_sync(_table_names)
    finally:
        await engine.dispose()


def _migrate(direction: str, target: str) -> None:
    child_env = os.environ.copy()
    child_env["CHANGEGUARD_TEST_DB_URL"] = DB_URL
    result = subprocess.run(
        [sys.executable, "-m", "alembic", direction, target],
        env=child_env,
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Alembic {direction} failed (exit {result.returncode})"
    )


async def _verify_schema(*, present: bool) -> None:
    engine = create_async_engine(DB_URL)
    try:
        async with engine.connect() as connection:
            if present:
                await connection.run_sync(_assert_job_schema)
                revision = await connection.scalar(
                    text("SELECT version_num FROM alembic_version")
                )
                assert revision == "0cfe6a6a43d3"
            else:
                assert "analysis_jobs" not in await connection.run_sync(_table_names)
                enum_type = await connection.scalar(
                    text("SELECT to_regtype('public.job_state')")
                )
                assert enum_type is None
    finally:
        await engine.dispose()


def test_upgrade_head_creates_analysis_jobs_schema() -> None:
    asyncio.run(_reset_database())
    try:
        _migrate("upgrade", "head")
        asyncio.run(_verify_schema(present=True))
        _migrate("downgrade", "base")
        asyncio.run(_verify_schema(present=False))
        _migrate("upgrade", "head")
        asyncio.run(_verify_schema(present=True))
    finally:
        asyncio.run(_reset_database())
