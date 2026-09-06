"""Detect changes to Python dependency definitions and lock files."""

from pathlib import PurePosixPath

from changeguard.findings import RiskFinding, RiskLevel
from changeguard.models import ChangeSet

PYTHON_DEPENDENCY_FILENAMES = frozenset(
    {
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "uv.lock",
    }
)


def detect_python_dependency_changes(
    change_set: ChangeSet,
) -> tuple[RiskFinding, ...]:
    matching_paths = sorted(
        {
            file.path
            for file in change_set.files
            if PurePosixPath(file.path).name in PYTHON_DEPENDENCY_FILENAMES
        }
    )

    if not matching_paths:
        return ()

    finding = RiskFinding(
        rule_id="python-dependency-change",
        level=RiskLevel.MEDIUM,
        summary=(
            "Python dependency files changed; "
            "review dependency and lockfile consistency."
        ),
        evidence_paths=tuple(matching_paths),
    )

    return (finding,)
