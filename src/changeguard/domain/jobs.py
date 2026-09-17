from dataclasses import dataclass
from enum import StrEnum


class JobState(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    QUEUED = "queued"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass(frozen=True, slots=True)
class Job:
    job_state: JobState
    job_id: str


@dataclass(frozen=True, slots=True)
class AnalysisJobIdentity:
    """Business uniqueness key for a persistent analysis job."""

    repository_owner: str
    repository_name: str
    pull_request_number: int
    base_sha: str
    head_sha: str
    analysis_version: str

    def __post_init__(self) -> None:
        if not self.repository_owner.strip():
            raise ValueError("repository_owner cannot be empty or whitespace-only")
        if not self.repository_name.strip():
            raise ValueError("repository_name cannot be empty or whitespace-only")
        if self.pull_request_number < 1:
            raise ValueError("pull_request_number must be positive")
        if not self.base_sha.strip():
            raise ValueError("base_sha cannot be empty or whitespace-only")
        if not self.head_sha.strip():
            raise ValueError("head_sha cannot be empty or whitespace-only")
        if not self.analysis_version.strip():
            raise ValueError("analysis_version cannot be empty or whitespace-only")


class InvalidJobTransition(ValueError):
    """Raised when a job cannot transition from one state to another."""


def validate_transition(current: JobState, target: JobState) -> None:
    if current == JobState.QUEUED and target == JobState.RUNNING:
        return
    if current == JobState.RUNNING and (
        target in [JobState.COMPLETED, JobState.FAILED, JobState.PARTIAL]
    ):
        return
    raise InvalidJobTransition()
