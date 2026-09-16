import asyncio

import httpx
import pytest
from pydantic import SecretStr

from changeguard.adapters.github import GithubClient
from changeguard.adapters.github_content import GitHubContentReader
from changeguard.config import GitHubSettings
from changeguard.domain.content import RemoteContentResult, Revision
from changeguard.domain.reports import CoverageState


def _read(
    **json_body: object,
) -> tuple[RemoteContentResult, dict[str, str | None]]:
    seen: dict[str, str | None] = {}

    def default_handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json=json_body)

    settings = GitHubSettings(token=SecretStr("ghp_test"))
    client = GithubClient(
        httpx.AsyncClient(transport=httpx.MockTransport(default_handler)), settings
    )
    reader = GitHubContentReader(client)
    result = asyncio.run(
        reader.get_content(
            "octo",
            "repo",
            "src/assets/README.md",
            "sha",
            Revision.HEAD,
        )
    )
    return result, seen


def test_github_content_file() -> None:
    result, seen = _read(
        type="file",
        encoding="base64",
        size=5362,
        name="README.md",
        path="README.md",
        content="aGVsbG8gd29ybGQ=",
        sha="3d21ec53a331a6f037a91c368710b99387d012c1",
    )

    assert seen["auth"] == "Bearer ghp_test"
    assert (
        seen["url"]
        == "https://api.github.com/repos/octo/repo/contents/src/assets/README.md?ref=sha"
    )
    assert result.coverage == ()
    assert result.content is not None
    assert result.content.text == "hello world"
    assert result.content.sha == "sha"
    assert result.content.revision == Revision.HEAD


def test_github_content_binds_requested_commit_sha_not_blob_sha() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "type": "file",
                "encoding": "base64",
                "size": 11,
                "name": "a.py",
                "path": "a.py",
                "content": "aGVsbG8gd29ybGQ=",
                "sha": "blob9f8e7d0000000000000000000000000000000",
            },
        )

    settings = GitHubSettings(token=SecretStr("ghp_test"))
    client = GithubClient(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)), settings
    )
    reader = GitHubContentReader(client)
    result = asyncio.run(
        reader.get_content("octo", "repo", "a.py", "commit123", Revision.HEAD)
    )

    assert result.content is not None
    assert result.content.sha == "commit123"


def test_github_content_symlink_is_partial_without_text() -> None:
    result, _ = _read(
        type="symlink",
        target="/path/to/real/file",
        size=23,
        name="link",
        path="bin/link",
        sha="452a98979c88e093d682cab404a3ec82babebb48",
    )

    assert result.content is None
    assert len(result.coverage) == 1
    assert result.coverage[0].state == CoverageState.PARTIAL
    assert result.coverage[0].reason.strip()


def test_github_content_oversized_is_partial_without_text() -> None:
    result, _ = _read(
        type="file",
        encoding="none",
        size=5242880,
        name="big.bin",
        path="big.bin",
        content="",
        sha="3d21ec53a331a6f037a91c368710b99387d012c1",
    )

    assert result.content is None
    assert len(result.coverage) == 1
    assert result.coverage[0].state == CoverageState.PARTIAL
    assert result.coverage[0].reason.strip()


def test_github_content_deleted_is_partial_without_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    settings = GitHubSettings(token=SecretStr("ghp_test"))
    client = GithubClient(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)), settings
    )
    reader = GitHubContentReader(client)
    result = asyncio.run(
        reader.get_content("octo", "repo", "gone.py", "sha", Revision.HEAD)
    )

    assert result.content is None
    assert len(result.coverage) == 1
    assert result.coverage[0].state == CoverageState.PARTIAL
    assert result.coverage[0].reason.strip()


def test_github_content_binary_is_partial_without_text() -> None:
    result, _ = _read(
        type="file",
        encoding="base64",
        size=4,
        name="logo.png",
        path="logo.png",
        content="/9j/4A==",
        sha="3d21ec53a331a6f037a91c368710b99387d012c1",
    )

    assert result.content is None
    assert len(result.coverage) == 1
    assert result.coverage[0].state == CoverageState.PARTIAL
    assert result.coverage[0].reason.strip()


def test_github_content_skips_when_over_remaining_budget() -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "type": "file",
                "encoding": "base64",
                "size": 5000,
                "name": "big.py",
                "path": "big.py",
                "content": "aGVsbG8=",
                "sha": "3d21ec53a331a6f037a91c368710b99387d012c1",
            },
        )

    settings = GitHubSettings(token=SecretStr("ghp_test"))
    client = GithubClient(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)), settings
    )
    reader = GitHubContentReader(client)
    result = asyncio.run(
        reader.get_content(
            "octo", "repo", "big.py", "sha", Revision.HEAD, remaining_bytes=1000
        )
    )

    assert result.content is None
    assert len(result.coverage) == 1
    assert result.coverage[0].state == CoverageState.PARTIAL
    assert result.coverage[0].reason.strip()


def test_github_content_returns_content_within_remaining_budget() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "type": "file",
                "encoding": "base64",
                "size": 11,
                "name": "small.py",
                "path": "small.py",
                "content": "aGVsbG8gd29ybGQ=",
                "sha": "3d21ec53a331a6f037a91c368710b99387d012c1",
            },
        )

    settings = GitHubSettings(token=SecretStr("ghp_test"))
    client = GithubClient(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)), settings
    )
    reader = GitHubContentReader(client)
    result = asyncio.run(
        reader.get_content(
            "octo", "repo", "small.py", "sha", Revision.HEAD, remaining_bytes=1000
        )
    )

    assert result.coverage == ()
    assert result.content is not None
    assert result.content.text == "hello world"


@pytest.mark.parametrize("bad_path", ["", "../secret", "/etc/passwd", "a\\b", "a\0b"])
def test_github_content_rejects_bad_path_before_request(bad_path: str) -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    settings = GitHubSettings(token=SecretStr("ghp_test"))
    client = GithubClient(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)), settings
    )
    reader = GitHubContentReader(client)

    with pytest.raises(ValueError):
        asyncio.run(reader.get_content("octo", "repo", bad_path, "sha", Revision.HEAD))

    assert called is False
