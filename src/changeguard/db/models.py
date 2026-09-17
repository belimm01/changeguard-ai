"""Persistence models for analysis jobs and their reports."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from changeguard.db.base import Base
from changeguard.domain.jobs import JobState

UNIQUE_JOB_IDENTITY = "uq_analysis_jobs_identity"


class AnalysisJobRecord(Base):
    """A persistent analysis job keyed by repository/PR/SHA/version identity."""

    __tablename__ = "analysis_jobs"
    __table_args__ = (
        UniqueConstraint(
            "repository_owner",
            "repository_name",
            "pull_request_number",
            "base_sha",
            "head_sha",
            "analysis_version",
            name=UNIQUE_JOB_IDENTITY,
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    repository_owner: Mapped[str] = mapped_column(String(255))
    repository_name: Mapped[str] = mapped_column(String(255))
    pull_request_number: Mapped[int] = mapped_column(Integer)
    base_sha: Mapped[str] = mapped_column(String(64))
    head_sha: Mapped[str] = mapped_column(String(64))
    analysis_version: Mapped[str] = mapped_column(String(64))

    state: Mapped[JobState] = mapped_column(
        Enum(
            JobState,
            name="job_state",
            values_callable=lambda enum: [member.value for member in enum],
        )
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    report_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    lease_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
