import asyncio

import httpx
from pydantic import SecretStr

from changeguard.adapters.github import GithubClient
from changeguard.adapters.github_content import GitHubContentReader
from changeguard.config import GitHubSettings
from changeguard.domain.content import Revision


def test_github_content() -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={
                "type": "file",
                "encoding": "base64",
                "size": 5362,
                "name": "README.md",
                "path": "README.md",
                "content": "aGVsbG8gd29ybGQ=",
                "sha": "3d21ec53a331a6f037a91c368710b99387d012c1",
                "url": "https://api.github.com/repos/octokit/octokit.rb/contents/README.md",
                "git_url": "https://api.github.com/repos/octokit/octokit.rb/git/blobs/3d21ec53a331a6f037a91c368710b99387d012c1",
                "html_url": "https://github.com/octokit/octokit.rb/blob/master/README.md",
                "download_url": "https://raw.githubusercontent.com/octokit/octokit.rb/master/README.md",
                "_links": {
                    "git": "https://api.github.com/repos/octokit/octokit.rb/git/blobs/3d21ec53a331a6f037a91c368710b99387d012c1",
                    "self": "https://api.github.com/repos/octokit/octokit.rb/contents/README.md",
                    "html": "https://github.com/octokit/octokit.rb/blob/master/README.md",
                },
            },
        )

    settings = GitHubSettings(token=SecretStr("ghp_test"))
    client = GithubClient(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)), settings
    )
    reader = GitHubContentReader(client)
    response = asyncio.run(
        reader.get_content("octo", "repo", "src/assets/README.md", "sha", Revision.HEAD)
    )

    assert seen["auth"] == "Bearer ghp_test"
    assert (
        seen["url"]
        == "https://api.github.com/repos/octo/repo/contents/src/assets/README.md?ref=sha"
    )
    assert response.text == "hello world"
    assert response.sha == "3d21ec53a331a6f037a91c368710b99387d012c1"
    assert response.revision == Revision.HEAD
