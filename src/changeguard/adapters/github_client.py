from dataclasses import dataclass

import httpx

from changeguard.adapters.github import parse_github_changed_files
from changeguard.config import GitHubSettings
from changeguard.domain.models import ChangeSet
from changeguard.domain.reports import Coverage


@dataclass(frozen=True, slots=True)
class RemoteFilesResult:
    changeset: ChangeSet
    coverage: tuple[Coverage, ...]


@dataclass(frozen=True, slots=True)
class PullRequestMetadata:
    owner: str
    name: str
    number: int
    base_sha: str
    head_sha: str
    title: str | None
    body: str | None
    api_url: str


class GitHubPullRequestReader:
    def __init__(self, client: httpx.AsyncClient, settings: GitHubSettings):
        self._client = client
        self._settings = settings

    async def read_metadata(
        self, owner: str, name: str, number: int
    ) -> PullRequestMetadata:
        rs = await self._client.get(
            url=f"{self._settings.base_url}/repos/{owner}/{name}/pulls/{number}",
            headers={
                "Authorization": f"Bearer {self._settings.token.get_secret_value()}"
            },
            timeout=self._settings.timeout_s,
        )
        rs.raise_for_status()
        data = rs.json()
        return PullRequestMetadata(
            owner=owner,
            name=name,
            number=number,
            base_sha=data["base"]["sha"],
            head_sha=data["head"]["sha"],
            title=data.get("title"),
            body=data.get("body"),
            api_url=data["url"],
        )

    async def read_changed_files(
        self, owner: str, name: str, number: int
    ) -> RemoteFilesResult:
        rs = await self._client.get(
            url=f"{self._settings.base_url}/repos/{owner}/{name}/pulls/{number}/files",
            headers={
                "Authorization": f"Bearer {self._settings.token.get_secret_value()}"
            },
            timeout=self._settings.timeout_s,
        )

        rs.raise_for_status()
        data = rs.json()
        return RemoteFilesResult(
            changeset=parse_github_changed_files(data),
            coverage=(),
        )
