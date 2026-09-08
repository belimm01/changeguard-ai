"""Translate GitHub changed-file payloads into ChangeGuard domain models."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from changeguard.domain.models import ChangedFile, ChangeSet, ChangeType


class GitHubChangedFile(BaseModel):
    """The GitHub fields required by ChangeGuard's first analysis rules."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    filename: str
    status: ChangeType
    additions: Annotated[int, Field(ge=0)]
    deletions: Annotated[int, Field(ge=0)]
    patch: str | None = None


_GITHUB_CHANGED_FILES = TypeAdapter(list[GitHubChangedFile])


def parse_github_changed_files(payload: object) -> ChangeSet:
    github_files = _GITHUB_CHANGED_FILES.validate_python(payload)
    domain_files = tuple(
        ChangedFile(
            path=file.filename,
            change_type=file.status,
            additions=file.additions,
            deletions=file.deletions,
            patch=file.patch,
        )
        for file in github_files
    )

    return ChangeSet(files=domain_files)
