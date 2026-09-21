import asyncio

import pytest
from sqlalchemy import func, select

from changeguard.db.models import AnalysisJobRecord
from changeguard.domain.jobs import (
    AnalysisJobIdentity,
    InvalidJobTransition,
    JobState,
)
from changeguard.repositories.analysis_jobs import AnalysisJobRepository
from integration.db._db import fresh_session, postgres_available


def _identity() -> AnalysisJobIdentity:
    return AnalysisJobIdentity(
        repository_owner="octocat",
        repository_name="hello-world",
        pull_request_number=42,
        base_sha="a" * 40,
        head_sha="b" * 40,
        analysis_version="v1",
    )


pytestmark = pytest.mark.skipif(
    not postgres_available(), reason="Postgres is not available"
)


def test_create_queued_inserts_one_row() -> None:
    async def scenario() -> None:
        async with fresh_session() as session:
            repo = AnalysisJobRepository(session)
            identity = AnalysisJobIdentity(
                repository_owner="octocat",
                repository_name="hello-world",
                pull_request_number=42,
                base_sha="a" * 40,
                head_sha="b" * 40,
                analysis_version="v1",
            )
            job = await repo.create_queued(identity)
            assert job.state == JobState.QUEUED
            count = (
                await session.execute(
                    select(func.count()).select_from(AnalysisJobRecord)
                )
            ).scalar_one()
            assert count == 1

    asyncio.run(scenario())


def test_create_queued_inserts_duplicate_row() -> None:
    async def scenario() -> None:
        async with fresh_session() as session:
            repo = AnalysisJobRepository(session)
            identity = AnalysisJobIdentity(
                repository_owner="octocat",
                repository_name="hello-world",
                pull_request_number=42,
                base_sha="a" * 40,
                head_sha="b" * 40,
                analysis_version="v1",
            )
            for _ in range(2):
                await repo.create_queued(identity)
            count = (
                await session.execute(
                    select(func.count()).select_from(AnalysisJobRecord)
                )
            ).scalar_one()
            assert count == 1

    asyncio.run(scenario())


def test_valid_path_running_then_completed_persists_report() -> None:
    async def scenario() -> None:
        async with fresh_session() as session:
            repo = AnalysisJobRepository(session)
            job = await repo.create_queued(_identity())

            await repo.mark_running(job)
            report = {"schema_version": 1, "risk": "low"}
            await repo.mark_completed(job, report)

            reloaded = (
                await session.execute(
                    select(AnalysisJobRecord).where(AnalysisJobRecord.id == job.id)
                )
            ).scalar_one()
            assert reloaded.state == JobState.COMPLETED
            assert reloaded.report_json == report
            assert reloaded.completed_at is not None

    asyncio.run(scenario())


def test_invalid_transition_leaves_stored_state_unchanged() -> None:
    async def scenario() -> None:
        async with fresh_session() as session:
            repo = AnalysisJobRepository(session)
            job = await repo.create_queued(_identity())

            with pytest.raises(InvalidJobTransition):
                await repo.mark_completed(job, {"schema_version": 1})

            reloaded = (
                await session.execute(
                    select(AnalysisJobRecord).where(AnalysisJobRecord.id == job.id)
                )
            ).scalar_one()
            assert reloaded.state == JobState.QUEUED
            assert reloaded.report_json is None
            assert reloaded.completed_at is None

    asyncio.run(scenario())
