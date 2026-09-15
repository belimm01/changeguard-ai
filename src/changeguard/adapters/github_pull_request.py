from dataclasses import dataclass

from changeguard.adapters.github import GithubClient, parse_github_changed_files
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
    def __init__(self, client: GithubClient, settings: GitHubSettings):
        self._client = client
        self._settings = settings

    async def read_metadata(
        self, owner: str, name: str, number: int
    ) -> PullRequestMetadata:
        link = f"/repos/{owner}/{name}/pulls/{number}"
        rs = await self._client.get_with_retry(link=link)
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
        link: str | None = f"/repos/{owner}/{name}/pulls/{number}/files"
        pages = 0
        reason: str | None = None
        while link is not None:
            rs = await self._client.get_with_retry(link=link)
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
