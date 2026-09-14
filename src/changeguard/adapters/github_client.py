from dataclasses import dataclass

import httpx
from httpx import Response

from changeguard.adapters.github import parse_github_changed_files
from changeguard.config import GitHubSettings
from changeguard.domain.models import ChangedFile, ChangeSet
from changeguard.domain.reports import Coverage, CoverageState


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
        collected: list[ChangedFile] = []
        link: str | None = (
            f"{self._settings.base_url}/repos/{owner}/{name}/pulls/{number}/files"
        )
        pages = 0
        reason: str | None = None
        while link is not None:
            rs = await self.request_changed_files(link=link)
            rs.raise_for_status()
            pages += 1
            collected.extend(parse_github_changed_files(rs.json()).files)

            if len(collected) > self._settings.max_files:
                collected = collected[: self._settings.max_files]
                reason = (
                    f"changed files truncated at max_files={self._settings.max_files}"
                )
                break

            next_link = rs.links.get("next")
            link = next_link["url"] if next_link is not None else None

            if link is not None and pages >= self._settings.max_pages:
                reason = f"pagination stopped at max_pages={self._settings.max_pages}"
                break

        coverage: tuple[Coverage, ...] = ()
        if reason is not None:
            coverage = (
                Coverage(
                    rule_id="github-changed-files",
                    target=f"{owner}/{name}#{number}",
                    state=CoverageState.PARTIAL,
                    reason=reason,
                ),
            )
        return RemoteFilesResult(
            changeset=ChangeSet(files=tuple(collected)),
            coverage=coverage,
        )

    async def request_changed_files(self, link: str) -> Response:
        rs = await self._client.get(
            url=link,
            headers={
                "Authorization": f"Bearer {self._settings.token.get_secret_value()}"
            },
            timeout=self._settings.timeout_s,
        )
        return rs
