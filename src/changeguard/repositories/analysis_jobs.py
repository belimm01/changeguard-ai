from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from changeguard.db.models import AnalysisJobRecord
from changeguard.domain.jobs import AnalysisJobIdentity, JobState, validate_transition


class AnalysisJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_queued(self, identity: AnalysisJobIdentity) -> AnalysisJobRecord:
        stmt = select(AnalysisJobRecord).where(
            AnalysisJobRecord.head_sha == identity.head_sha,
            AnalysisJobRecord.base_sha == identity.base_sha,
            AnalysisJobRecord.analysis_version == identity.analysis_version,
            AnalysisJobRecord.pull_request_number == identity.pull_request_number,
            AnalysisJobRecord.repository_name == identity.repository_name,
            AnalysisJobRecord.repository_owner == identity.repository_owner,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing
        job = AnalysisJobRecord(
            repository_owner=identity.repository_owner,
            repository_name=identity.repository_name,
            pull_request_number=identity.pull_request_number,
            base_sha=identity.base_sha,
            head_sha=identity.head_sha,
            analysis_version=identity.analysis_version,
            state=JobState.QUEUED,
        )
        self._session.add(job)
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def mark_running(self, job: AnalysisJobRecord) -> AnalysisJobRecord:
        validate_transition(job.state, JobState.RUNNING)
        job.state = JobState.RUNNING
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def mark_completed(
        self, job: AnalysisJobRecord, report_json: dict[str, Any]
    ) -> AnalysisJobRecord:
        validate_transition(job.state, JobState.COMPLETED)
        job.state = JobState.COMPLETED
        job.report_json = report_json
        job.completed_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def mark_partial(
        self, job: AnalysisJobRecord, report_json: dict[str, Any]
    ) -> AnalysisJobRecord:
        validate_transition(job.state, JobState.PARTIAL)
        job.state = JobState.PARTIAL
        job.report_json = report_json
        job.completed_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(job)
        return job
