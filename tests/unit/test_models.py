from dataclasses import FrozenInstanceError

import pytest

from changeguard.models import ChangedFile, ChangeSet, ChangeType


def test_change_type_has_stable_string_values() -> None:
    assert [item.value for item in ChangeType] == [
        "added",
        "modified",
        "deleted",
        "renamed",
    ]


def test_changed_file_accepts_valid_values() -> None:
    changed_file = ChangedFile(
        path="src/changeguard/models.py",
        change_type=ChangeType.MODIFIED,
        additions=1,
        deletions=0,
    )

    assert changed_file.path == "src/changeguard/models.py"


@pytest.mark.parametrize(
    "path",
    [
        "",
        "   ",
        "/etc/passwd",
        "../changeguard/models.py",
        "src/../models.py",
        "src\\changeguard\\models.py",
        "src/changeguard/\0models.py",
    ],
)
def test_rejects_unsafe_repository_paths(path: str) -> None:
    with pytest.raises(ValueError):
        ChangedFile(
            path=path,
            change_type=ChangeType.MODIFIED,
            additions=1,
            deletions=0,
        )


def test_accepts_double_dots_inside_a_filename() -> None:
    changed_file = ChangedFile(
        path="src/version..backup.py",
        change_type=ChangeType.MODIFIED,
        additions=1,
        deletions=0,
    )

    assert changed_file.path == "src/version..backup.py"


@pytest.mark.parametrize(
    ("additions", "deletions"),
    [
        (-1, 0),
        (0, -1),
    ],
)
def test_rejects_negative_line_counts(additions: int, deletions: int) -> None:
    with pytest.raises(ValueError):
        ChangedFile(
            path="src/changeguard/models.py",
            change_type=ChangeType.MODIFIED,
            additions=additions,
            deletions=deletions,
        )


def test_accepts_missing_patch() -> None:
    changed_file = ChangedFile(
        path="src/changeguard/models.py",
        patch=None,
        change_type=ChangeType.MODIFIED,
        additions=1,
        deletions=0,
    )

    assert changed_file.patch is None


def test_changed_file_is_immutable() -> None:
    changed_file = ChangedFile(
        patch=None,
        change_type=ChangeType.MODIFIED,
        additions=1,
        deletions=0,
        path="changeguard/models.py",
    )
    field_name = "path"
    with pytest.raises(FrozenInstanceError):
        setattr(changed_file, field_name, "changed.py")


def test_calculates_change_set_totals() -> None:
    changed_file = ChangedFile(
        patch=None,
        change_type=ChangeType.MODIFIED,
        additions=3,
        deletions=2,
        path="src/changeguard/models.py",
    )
    changed_file_2 = ChangedFile(
        patch=None,
        change_type=ChangeType.MODIFIED,
        additions=5,
        deletions=7,
        path="tests/unit/test_models.py",
    )
    change_set = ChangeSet(files=(changed_file, changed_file_2))
    assert change_set.total_additions == 8
    assert change_set.total_deletions == 9


def test_empty_change_set_has_zero_totals() -> None:
    change_set = ChangeSet(files=())

    assert change_set.total_additions == 0
    assert change_set.total_deletions == 0
