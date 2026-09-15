"""Domain models for pull-request changes.

Repository paths and patches originate outside our trust boundary. Keep these
models independent from GitHub, HTTP, database, and LLM libraries.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath


class ChangeType(StrEnum):
    """Change types used by source-control providers."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass(frozen=True, slots=True)
class ChangedFile:
    """A single file reported as changed in a pull request."""

    path: str
    change_type: ChangeType
    additions: int
    deletions: int
    patch: str | None = None

    def __post_init__(self) -> None:
        validate_relative_path(self.path)
        if self.additions < 0:
            raise ValueError("additions cannot be negative")
        if self.deletions < 0:
            raise ValueError("deletions cannot be negative")


@dataclass(frozen=True, slots=True)
class ChangeSet:
    """An immutable collection of files changed by one pull request."""

    files: tuple[ChangedFile, ...]

    @property
    def total_additions(self) -> int:
        return sum(file.additions for file in self.files)

    @property
    def total_deletions(self) -> int:
        return sum(file.deletions for file in self.files)


def validate_relative_path(path: str) -> None:
    if not path.strip():
        raise ValueError("path cannot be empty or whitespace-only")
    if "\0" in path:
        raise ValueError("path cannot contain a null byte")
    if "\\" in path:
        raise ValueError("path must use POSIX separators")

    pure_path = PurePosixPath(path)
    if pure_path.is_absolute():
        raise ValueError("path must be relative")
    if ".." in pure_path.parts:
        raise ValueError("path cannot contain '..'")
