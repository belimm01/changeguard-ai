from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from changeguard.db.models import UNIQUE_JOB_IDENTITY, AnalysisJobRecord
from changeguard.domain.jobs import AnalysisJobIdentity, JobState, validate_transition


class AnalysisJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_queued(self, identity: AnalysisJobIdentity) -> AnalysisJobRecord:
        values = {
            "repository_owner": identity.repository_owner,
            "repository_name": identity.repository_name,
            "pull_request_number": identity.pull_request_number,
            "base_sha": identity.base_sha,
            "head_sha": identity.head_sha,
            "analysis_version": identity.analysis_version,
        }
        statement = (
            insert(AnalysisJobRecord)
            .values(**values, state=JobState.QUEUED)
            .on_conflict_do_nothing(constraint=UNIQUE_JOB_IDENTITY)
            .returning(AnalysisJobRecord)
        )
        try:
            job = (await self._session.execute(statement)).scalar_one_or_none()
            if job is None:
                existing = select(AnalysisJobRecord).filter_by(**values)
                job = (await self._session.execute(existing)).scalar_one()
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        await self._session.refresh(job)
        return job

    async def _save(self, job: AnalysisJobRecord) -> AnalysisJobRecord:
        try:
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        await self._session.refresh(job)
        return job

    async def mark_running(self, job: AnalysisJobRecord) -> AnalysisJobRecord:
        validate_transition(job.state, JobState.RUNNING)
        job.state = JobState.RUNNING
        return await self._save(job)

    async def mark_completed(
        self, job: AnalysisJobRecord, report_json: dict[str, Any]
    ) -> AnalysisJobRecord:
        validate_transition(job.state, JobState.COMPLETED)
        job.state = JobState.COMPLETED
        job.report_json = report_json
        job.completed_at = datetime.now(UTC)
        return await self._save(job)

    async def mark_partial(
        self, job: AnalysisJobRecord, report_json: dict[str, Any]
    ) -> AnalysisJobRecord:
        validate_transition(job.state, JobState.PARTIAL)
        job.state = JobState.PARTIAL
        job.report_json = report_json
        job.completed_at = datetime.now(UTC)
        return await self._save(job)

    async def mark_failed(
        self,
        job: AnalysisJobRecord,
        reason: str,
        report_json: dict[str, Any] | None = None,
    ) -> AnalysisJobRecord:
        validate_transition(job.state, JobState.FAILED)
        job.state = JobState.FAILED
        # Persist only bounded public codes, never exception text or repository content.
        job.failure_reason = (
            reason
            if reason in {"analysis_failed", "upstream_timeout", "upstream_unavailable"}
            else "analysis_failed"
        )
        job.report_json = report_json
        job.completed_at = datetime.now(UTC)
        return await self._save(job)
