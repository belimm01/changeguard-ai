import pytest

from changeguard.domain.jobs import (
    AnalysisJobIdentity,
    InvalidJobTransition,
    Job,
    JobState,
    validate_transition,
)


def _identity(**overrides: object) -> AnalysisJobIdentity:
    fields: dict[str, object] = {
        "repository_owner": "octocat",
        "repository_name": "hello-world",
        "pull_request_number": 42,
        "base_sha": "a" * 40,
        "head_sha": "b" * 40,
        "analysis_version": "v1",
    }
    fields.update(overrides)
    return AnalysisJobIdentity(**fields)  # type: ignore[arg-type]


def test_analysis_job_identity_equal_and_hashable() -> None:
    first = _identity()
    second = _identity()
    assert first == second
    assert hash(first) == hash(second)
    assert len({first, second}) == 1


def test_analysis_job_identity_distinct_on_head_sha() -> None:
    assert _identity() != _identity(head_sha="c" * 40)


@pytest.mark.parametrize(
    "field",
    [
        "repository_owner",
        "repository_name",
        "base_sha",
        "head_sha",
        "analysis_version",
    ],
)
def test_analysis_job_identity_rejects_blank_fields(field: str) -> None:
    with pytest.raises(ValueError):
        _identity(**{field: "   "})


def test_analysis_job_identity_rejects_non_positive_pr_number() -> None:
    with pytest.raises(ValueError):
        _identity(pull_request_number=0)


def test_job() -> None:
    job = Job(job_id="123", job_state=JobState.RUNNING)
    assert job.job_id == "123"
    assert job.job_state == JobState.RUNNING


def test_validate_transition() -> None:
    with pytest.raises(InvalidJobTransition):
        validate_transition(JobState.QUEUED, JobState.COMPLETED)

    validate_transition(JobState.QUEUED, JobState.RUNNING)
