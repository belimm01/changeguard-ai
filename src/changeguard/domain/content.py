from dataclasses import dataclass
from enum import StrEnum

from changeguard.domain.models import validate_relative_path


class Revision(StrEnum):
    BASE = "base"
    HEAD = "head"


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
