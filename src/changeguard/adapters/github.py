"""Translate GitHub changed-file payloads into ChangeGuard domain models."""

import asyncio
from typing import Annotated

import httpx
from httpx import Response
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from changeguard.config import GitHubSettings
from changeguard.domain.models import ChangedFile, ChangeSet, ChangeType

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def _is_retryable(response: Response) -> bool:
    if response.status_code in _RETRYABLE_STATUS:
        return True
    return (
        response.status_code == 403
        and response.headers.get("x-ratelimit-remaining") == "0"
    )


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


class GithubClient:
    def __init__(self, client: httpx.AsyncClient, settings: GitHubSettings):
        self._client = client
        self._settings = settings

    async def get_with_retry(self, link: str) -> Response:
        last_error: httpx.HTTPError | None = None
        full_url = link
        for attempt in range(self._settings.max_retries):
            try:
                if not link.startswith("https://"):
                    full_url = f"{self._settings.base_url}{link}"
                rs = await self._client.get(
                    url=full_url,
                    headers={
                        "Authorization": f"Bearer {self._settings.token.get_secret_value()}"
                    },
                    timeout=self._settings.timeout_s,
                )
                rs.raise_for_status()
                return rs
            except httpx.HTTPStatusError as e:
                if not _is_retryable(e.response):
                    raise
                last_error = e
            except httpx.TimeoutException as e:
                last_error = e
            if attempt + 1 < self._settings.max_retries:
                await asyncio.sleep(2**attempt)
        assert last_error is not None
        raise last_error
