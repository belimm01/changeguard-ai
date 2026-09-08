import pytest

from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.models import ChangedFile, ChangeSet, ChangeType
from changeguard.rules.python_dependencies import detect_python_dependency_changes


def changed_file(
    path: str,
    *,
    change_type: ChangeType = ChangeType.MODIFIED,
    patch: str | None = None,
) -> ChangedFile:
    return ChangedFile(
        path=path,
        change_type=change_type,
        additions=1,
        deletions=0,
        patch=patch,
    )


def test_risk_finding_exposes_level_value() -> None:
    finding = RiskFinding(
        rule_id="example-rule",
        level=RiskLevel.LOW,
        summary="Example advisory finding",
        evidence_paths=("example.txt",),
    )

    assert finding.level == "low"


def test_returns_no_finding_without_dependency_changes() -> None:
    change_set = ChangeSet(files=(changed_file("src/changeguard/models.py"),))

    findings = detect_python_dependency_changes(change_set)

    assert findings == ()


def test_reports_a_changed_dependency_file() -> None:
    change_set = ChangeSet(files=(changed_file("requirements.txt"),))

    findings = detect_python_dependency_changes(change_set)

    assert findings == (
        RiskFinding(
            rule_id="python-dependency-change",
            level=RiskLevel.MEDIUM,
            summary=(
                "Python dependency files changed; "
                "review dependency and lockfile consistency."
            ),
            evidence_paths=("requirements.txt",),
        ),
    )


@pytest.mark.parametrize(
    "filename",
    [
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "uv.lock",
    ],
)
def test_detects_every_supported_dependency_filename(filename: str) -> None:
    path = f"services/api/{filename}"
    change_set = ChangeSet(files=(changed_file(path),))

    findings = detect_python_dependency_changes(change_set)

    assert findings[0].evidence_paths == (path,)


def test_aggregates_sorted_unique_dependency_paths() -> None:
    change_set = ChangeSet(
        files=(
            changed_file("services/web/uv.lock"),
            changed_file("src/main.py"),
            changed_file("services/api/pyproject.toml"),
            changed_file("services/web/uv.lock"),
        )
    )

    findings = detect_python_dependency_changes(change_set)

    assert len(findings) == 1
    assert findings[0].evidence_paths == (
        "services/api/pyproject.toml",
        "services/web/uv.lock",
    )


def test_ignores_similarly_named_files() -> None:
    change_set = ChangeSet(
        files=(
            changed_file("services/api/not-pyproject.toml"),
            changed_file("pyproject.toml.backup"),
            changed_file("requirements.txt.old"),
        )
    )

    assert detect_python_dependency_changes(change_set) == ()


def test_detects_dependency_files_in_nested_directories() -> None:
    path = "services/api/pyproject.toml"
    change_set = ChangeSet(files=(changed_file(path),))

    findings = detect_python_dependency_changes(change_set)

    assert findings[0].evidence_paths == (path,)


@pytest.mark.parametrize("change_type", list(ChangeType))
def test_detects_every_change_type(change_type: ChangeType) -> None:
    path = "uv.lock"
    change_set = ChangeSet(files=(changed_file(path, change_type=change_type),))

    findings = detect_python_dependency_changes(change_set)

    assert findings[0].evidence_paths == (path,)


def test_uses_file_paths_without_inspecting_patch_contents() -> None:
    change_set = ChangeSet(
        files=(
            changed_file("src/main.py", patch="+++ pyproject.toml"),
            changed_file("services/api/pyproject.toml", patch=None),
        )
    )

    findings = detect_python_dependency_changes(change_set)

    assert findings[0].evidence_paths == ("services/api/pyproject.toml",)
