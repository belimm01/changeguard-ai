import base64

from changeguard.adapters.github import GithubClient
from changeguard.domain.content import FileContent, Revision


class GitHubContentReader:
    def __init__(self, client: GithubClient):
        self._client = client

    async def get_content(
        self, owner: str, name: str, path: str, sha: str, ref: Revision
    ) -> FileContent:
        url = f"/repos/{owner}/{name}/contents/{path}?ref={sha}"
        rs = await self._client.get_with_retry(link=url)
        data = rs.json()
        return FileContent(
            sha=data["sha"],
            text=base64.b64decode(data["content"]).decode("utf-8"),
            revision=ref,
        )
