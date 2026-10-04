import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from changeguard.db.models import AnalysisJobRecord
from changeguard.domain.jobs import (
    AnalysisJobIdentity,
    InvalidJobTransition,
    JobState,
)
from changeguard.domain.reports import (
    AnalysisReport,
    Coverage,
    CoverageState,
    ReportStatus,
)
from changeguard.reporting import SCHEMA_VERSION, serialize_report
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


def _report(*, partial: bool = False) -> dict[str, object]:
    identity = _identity()
    return serialize_report(
        AnalysisReport(
            analysis_version=identity.analysis_version,
            repository=f"{identity.repository_owner}/{identity.repository_name}",
            pull_request=str(identity.pull_request_number),
            base_sha=identity.base_sha,
            head_sha=identity.head_sha,
            status=ReportStatus.PARTIAL if partial else ReportStatus.COMPLETE,
            findings=(),
            evidence=(),
            coverage=(
                Coverage(
                    rule_id="example-rule",
                    target="docs/api.md",
                    state=CoverageState.PARTIAL if partial else CoverageState.SUPPORTED,
                    reason="Fixture coverage",
                ),
            ),
        )
    )


@pytest.mark.parametrize("partial", [False, True])
def test_terminal_report_survives_a_new_session(partial: bool) -> None:
    async def scenario() -> None:
        async with fresh_session() as session:
            repo = AnalysisJobRepository(session)
            job = await repo.create_queued(_identity())
            await repo.mark_running(job)
            report = _report(partial=partial)
            if partial:
                await repo.mark_partial(job, report)
            else:
                await repo.mark_completed(job, report)
            assert session.bind is not None
            async with AsyncSession(session.bind) as reader:
                stored = await reader.get(AnalysisJobRecord, job.id)
                assert stored is not None
                assert stored.state == (
                    JobState.PARTIAL if partial else JobState.COMPLETED
                )
                assert stored.report_json == report
                assert stored.report_json["schema_version"] == SCHEMA_VERSION
                assert stored.report_json["base_sha"] == _identity().base_sha
                assert stored.report_json["head_sha"] == _identity().head_sha
                assert stored.completed_at is not None
                assert stored.requested_at is not None

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


@pytest.mark.parametrize(
    "reason, expected",
    [
        ("upstream_timeout", "upstream_timeout"),
        ("upstream_unavailable", "upstream_unavailable"),
        ("analysis_failed", "analysis_failed"),
        ("Authorization: Bearer fake-test-credential", "analysis_failed"),
        (
            "diff --git a/private.py b/private.py\n+confidential fixture",
            "analysis_failed",
        ),
        ("arbitrary repository contents", "analysis_failed"),
        ("x" * 2048, "analysis_failed"),
        ("", "analysis_failed"),
    ],
)
def test_failed_reason_is_safe_and_bounded(reason: str, expected: str) -> None:
    async def scenario() -> None:
        async with fresh_session() as session:
            repo = AnalysisJobRepository(session)
            job = await repo.create_queued(_identity())
            await repo.mark_running(job)
            await repo.mark_failed(job, reason)
            assert session.bind is not None
            async with AsyncSession(session.bind) as reader:
                stored = await reader.get(AnalysisJobRecord, job.id)
                assert stored is not None
                assert stored.state == JobState.FAILED
                assert stored.failure_reason == expected
                assert stored.completed_at is not None
                assert stored.report_json is None
                limit = AnalysisJobRecord.failure_reason.type.length
                assert limit is not None
                assert len(stored.failure_reason) <= limit

    asyncio.run(scenario())


def test_failed_job_can_preserve_a_versioned_report() -> None:
    async def scenario() -> None:
        async with fresh_session() as session:
            repo = AnalysisJobRepository(session)
            job = await repo.create_queued(_identity())
            await repo.mark_running(job)
            report = _report(partial=True)
            await repo.mark_failed(job, "upstream_timeout", report_json=report)
            assert session.bind is not None
            async with AsyncSession(session.bind) as reader:
                stored = await reader.get(AnalysisJobRecord, job.id)
                assert stored is not None
                assert stored.state == JobState.FAILED
                assert stored.report_json == report

    asyncio.run(scenario())


def test_invalid_transition_to_failed_leaves_stored_state_unchanged() -> None:
    async def scenario() -> None:
        async with fresh_session() as session:
            repo = AnalysisJobRepository(session)
            job = await repo.create_queued(_identity())

            with pytest.raises(InvalidJobTransition):
                await repo.mark_failed(job, reason="boom")

            reloaded = (
                await session.execute(
                    select(AnalysisJobRecord).where(AnalysisJobRecord.id == job.id)
                )
            ).scalar_one()
            assert reloaded.state == JobState.QUEUED
            assert reloaded.failure_reason is None
            assert reloaded.completed_at is None

    asyncio.run(scenario())


def test_concurrent_duplicate_returns_the_same_job() -> None:
    async def scenario() -> None:
        async with fresh_session() as setup:
            assert setup.bind is not None
            factory = async_sessionmaker(setup.bind, expire_on_commit=False)
            barrier = asyncio.Barrier(2)

            async def create() -> int:
                async with factory() as session:
                    await barrier.wait()
                    job = await AnalysisJobRepository(session).create_queued(
                        _identity()
                    )
                    return job.id

            first, second = await asyncio.wait_for(
                asyncio.gather(create(), create()),
                timeout=10,
            )
            assert first == second
            async with factory() as reader:
                count = await reader.scalar(
                    select(func.count()).select_from(AnalysisJobRecord)
                )
                assert count == 1

    asyncio.run(scenario())


def test_failed_insert_rolls_back_and_session_can_be_reused() -> None:
    async def scenario() -> None:
        async with fresh_session() as session:
            repo = AnalysisJobRepository(session)
            identity = _identity()
            session.add(
                AnalysisJobRecord(
                    repository_owner=identity.repository_owner,
                    repository_name=identity.repository_name,
                    pull_request_number=identity.pull_request_number,
                    base_sha=identity.base_sha,
                    head_sha=identity.head_sha,
                    analysis_version=identity.analysis_version,
                    # Omitting the non-null state causes a real database error.
                )
            )
            with pytest.raises(IntegrityError):
                await repo.create_queued(identity)
            job = await repo.create_queued(identity)
            assert job.state == JobState.QUEUED

    asyncio.run(scenario())
