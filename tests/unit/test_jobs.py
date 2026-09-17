import pytest

from changeguard.domain.jobs import (
    InvalidJobTransition,
    Job,
    JobState,
    validate_transition,
)


def test_job() -> None:
    job = Job(job_id="123", job_state=JobState.RUNNING)
    assert job.job_id == "123"
    assert job.job_state == JobState.RUNNING


def test_validate_transition() -> None:
    with pytest.raises(InvalidJobTransition):
        validate_transition(JobState.QUEUED, JobState.COMPLETED)

    validate_transition(JobState.QUEUED, JobState.RUNNING)
