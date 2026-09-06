from copy import deepcopy

import pytest
from pydantic import ValidationError

from changeguard.adapters.github import GitHubChangedFile, parse_github_changed_files
from changeguard.models import ChangedFile, ChangeSet, ChangeType


def github_file(
    filename: str = "src/changeguard/models.py",
    *,
    status: str = "modified",
    additions: int = 3,
    deletions: int = 1,
    patch: str | None = None,
) -> dict[str, object]:
    return {
        "filename": filename,
        "status": status,
        "additions": additions,
        "deletions": deletions,
        "patch": patch,
    }


def test_github_changed_file_schema_parses_required_fields() -> None:
    github_file = GitHubChangedFile.model_validate(
        {
            "filename": "src/changeguard/models.py",
            "status": "modified",
            "additions": 3,
            "deletions": 1,
        }
    )

    assert github_file.status is ChangeType.MODIFIED
    assert github_file.patch is None


def test_translates_a_valid_github_payload() -> None:
    payload = [
        github_file(patch="@@ -1 +1 @@"),
        github_file(
            "README.md",
            status="deleted",
            additions=0,
            deletions=8,
        ),
    ]

    change_set = parse_github_changed_files(payload)

    assert change_set == ChangeSet(
        files=(
            ChangedFile(
                path="src/changeguard/models.py",
                change_type=ChangeType.MODIFIED,
                additions=3,
                deletions=1,
                patch="@@ -1 +1 @@",
            ),
            ChangedFile(
                path="README.md",
                change_type=ChangeType.DELETED,
                additions=0,
                deletions=8,
                patch=None,
            ),
        )
    )


def test_translates_an_empty_payload() -> None:
    assert parse_github_changed_files([]) == ChangeSet(files=())


def test_ignores_extra_github_fields_without_mutating_input() -> None:
    payload = [
        {
            **github_file("renamed.py", status="renamed"),
            "sha": "abc123",
            "blob_url": "https://example.invalid/blob",
            "previous_filename": "old.py",
        }
    ]
    original = deepcopy(payload)

    change_set = parse_github_changed_files(payload)

    assert change_set.files[0].path == "renamed.py"
    assert payload == original


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        [{"filename": "README.md"}],
        [
            {
                "filename": "README.md",
                "status": "unknown",
                "additions": 1,
                "deletions": 0,
            }
        ],
    ],
)
def test_rejects_malformed_payloads(payload: object) -> None:
    with pytest.raises(ValidationError):
        parse_github_changed_files(payload)


@pytest.mark.parametrize(
    ("additions", "deletions"),
    [
        (-1, 0),
        (0, -1),
    ],
)
def test_rejects_negative_line_counts(additions: int, deletions: int) -> None:
    with pytest.raises(ValidationError):
        parse_github_changed_files(
            [github_file(additions=additions, deletions=deletions)]
        )


def test_rejects_an_unsafe_repository_path() -> None:
    with pytest.raises(ValueError):
        parse_github_changed_files([github_file("../secret.txt")])


@pytest.mark.parametrize("status", [item.value for item in ChangeType])
def test_translates_every_supported_status(status: str) -> None:
    change_set = parse_github_changed_files([github_file(status=status)])

    assert change_set.files[0].change_type is ChangeType(status)
