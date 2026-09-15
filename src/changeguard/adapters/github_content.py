import base64

from changeguard.adapters.github import GithubClient
from changeguard.domain.content import FileContent, RemoteContentResult, Revision
from changeguard.domain.reports import Coverage, CoverageState


class GitHubContentReader:
    def __init__(self, client: GithubClient):
        self._client = client

    async def get_content(
        self, owner: str, name: str, path: str, sha: str, ref: Revision
    ) -> RemoteContentResult:
        url = f"/repos/{owner}/{name}/contents/{path}?ref={sha}"
        rs = await self._client.get_with_retry(link=url)
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
        return RemoteContentResult(
            content=FileContent(
                sha=data["sha"],
                text=base64.b64decode(data["content"]).decode("utf-8"),
                revision=ref,
            ),
            coverage=(),
        )
