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
