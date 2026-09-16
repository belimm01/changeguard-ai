from dataclasses import dataclass
from enum import StrEnum

from changeguard.domain.models import validate_relative_path
from changeguard.domain.reports import Coverage


class Revision(StrEnum):
    BASE = "base"
    HEAD = "head"


@dataclass(frozen=True, slots=True)
class DiffLineEvidence:
    path: str
    side: Revision
    start_line: int
    end_line: int
    sha: str

    def __post_init__(self) -> None:
        validate_relative_path(self.path)
        if self.start_line < 1:
            raise ValueError("start_line must be greater than 0")
        if self.end_line < 1:
            raise ValueError("end_line must be greater than 0")
        if self.start_line > self.end_line:
            raise ValueError("start_line must be less than or equal to end_line")
        if not self.sha.strip():
            raise ValueError("sha cannot be empty or whitespace-only")

    @classmethod
    def from_content(
        cls,
        content: "FileContent",
        path: str,
        start_line: int,
        end_line: int,
    ) -> "DiffLineEvidence":
        return cls(
            path=path,
            start_line=start_line,
            end_line=end_line,
            side=content.revision,
            sha=content.sha,
        )


@dataclass(frozen=True, slots=True)
class FileContentRef:
    """A file's contents at a specific revision."""

    owner: str
    name: str
    path: str
    revision: Revision
    sha: str

    def __post_init__(self) -> None:
        validate_relative_path(self.path)
        if not self.owner.strip():
            raise ValueError("owner cannot be empty or whitespace-only")
        if not self.name.strip():
            raise ValueError("name cannot be empty or whitespace-only")
        if not self.sha.strip():
            raise ValueError("sha cannot be empty or whitespace-only")


@dataclass(frozen=True, slots=True)
class FileContent:
    """A file's contents at a specific revision."""

    sha: str
    text: str
    revision: Revision


@dataclass(frozen=True, slots=True)
class RemoteContentResult:
    coverage: tuple[Coverage, ...]
    content: FileContent | None = None
