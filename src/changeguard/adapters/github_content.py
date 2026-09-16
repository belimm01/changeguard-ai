import base64

from httpx import HTTPStatusError

from changeguard.adapters.github import GithubClient
from changeguard.domain.content import FileContent, RemoteContentResult, Revision
from changeguard.domain.models import validate_relative_path
from changeguard.domain.reports import Coverage, CoverageState


class GitHubContentReader:
    def __init__(self, client: GithubClient):
        self._client = client

    async def get_content(
        self,
        owner: str,
        name: str,
        path: str,
        sha: str,
        ref: Revision,
        remaining_bytes: int | None = None,
    ) -> RemoteContentResult:
        validate_relative_path(path)
        url = f"/repos/{owner}/{name}/contents/{path}?ref={sha}"
        try:
            rs = await self._client.get_with_retry(link=url)
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return RemoteContentResult(
                    coverage=(
                        Coverage(
                            rule_id="github-content",
                            target=path,
                            state=CoverageState.PARTIAL,
                            reason="not found",
                        ),
                    )
                )
            raise
        data = rs.json()
        if data["type"] != "file":
            return RemoteContentResult(
                coverage=(
                    Coverage(
                        rule_id="github-content",
                        target=path,
                        state=CoverageState.PARTIAL,
                        reason="not a regular file",
                    ),
                )
            )
        if remaining_bytes is not None and data["size"] > remaining_bytes:
            return RemoteContentResult(
                coverage=(
                    Coverage(
                        rule_id="github-content",
                        target=path,
                        state=CoverageState.PARTIAL,
                        reason="aggregate content byte limit exceeded",
                    ),
                )
            )
        if data["encoding"] != "base64":
            return RemoteContentResult(
                coverage=(
                    Coverage(
                        rule_id="github-content",
                        target=path,
                        state=CoverageState.PARTIAL,
                        reason="content too large to fetch",
                    ),
                )
            )
        try:
            text = base64.b64decode(data["content"]).decode("utf-8")
        except UnicodeDecodeError:
            return RemoteContentResult(
                coverage=(
                    Coverage(
                        rule_id="github-content",
                        target=path,
                        state=CoverageState.PARTIAL,
                        reason="binary content",
                    ),
                )
            )
        return RemoteContentResult(
            content=FileContent(
                sha=data["sha"],
                text=text,
                revision=ref,
            ),
            coverage=(),
        )
