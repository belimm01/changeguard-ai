import asyncio

import httpx
import pytest
from pydantic import SecretStr

from changeguard.adapters.github_client import GitHubPullRequestReader
from changeguard.config import GitHubSettings
from changeguard.domain.models import ChangeType
from changeguard.domain.reports import CoverageState


def test_read_changed_files_with_pagination() -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        if "page=2" in str(request.url):
            return httpx.Response(
                200,
                json=[
                    {
                        "sha": "bbcd538c8e72b8c175046e27cc8f907076331401",
                        "filename": "b.txt",
                        "status": "added",
                        "additions": 103,
                        "deletions": 21,
                        "changes": 124,
                        "blob_url": "https://github.com/octocat/Hello-World/blob/6dcb.../file1.txt",
                        "raw_url": "https://github.com/octocat/Hello-World/raw/6dcb.../file1.txt",
                        "contents_url": "https://api.github.com/repos/octocat/Hello-World/contents/file1.txt?ref=6dcb...",
                        "patch": "@@ -132,7 +132,7 @@ module Test ...",
                    },
                ],
            )
        return httpx.Response(
            200,
            headers={
                "link": '<https://api.github.com/repos/octo/repo/pulls/123/files?page=2>; rel="next", <https://api.github.com/repos/octo/repo/pulls/123/files?page=2>; rel="last"'
            },
            json=[
                {
                    "sha": "bbcd538c8e72b8c175046e27cc8f907076331401",
                    "filename": "a.txt",
                    "status": "added",
                    "additions": 103,
                    "deletions": 21,
                    "changes": 124,
                    "blob_url": "https://github.com/octocat/Hello-World/blob/6dcb.../file1.txt",
                    "raw_url": "https://github.com/octocat/Hello-World/raw/6dcb.../file1.txt",
                    "contents_url": "https://api.github.com/repos/octocat/Hello-World/contents/file1.txt?ref=6dcb...",
                    "patch": "@@ -132,7 +132,7 @@ module Test ...",
                },
            ],
        )

    settings = GitHubSettings(token=SecretStr("ghp_test"))
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    reader = GitHubPullRequestReader(client, settings)

    changed_files = asyncio.run(reader.read_changed_files("octo", "repo", 123))

    assert seen["auth"] == "Bearer ghp_test"
    assert (
        seen["url"] == "https://api.github.com/repos/octo/repo/pulls/123/files?page=2"
    )
    assert len(changed_files.changeset.files) == 2
    assert changed_files.coverage == ()
    assert changed_files.changeset.files[0].path == "a.txt"
    assert changed_files.changeset.files[1].path == "b.txt"


def test_read_changed_files_with_pagination_returns_partial_state() -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        if "page=2" in str(request.url):
            return httpx.Response(
                200,
                json=[
                    {
                        "sha": "bbcd538c8e72b8c175046e27cc8f907076331401",
                        "filename": "b.txt",
                        "status": "added",
                        "additions": 103,
                        "deletions": 21,
                        "changes": 124,
                        "blob_url": "https://github.com/octocat/Hello-World/blob/6dcb.../file1.txt",
                        "raw_url": "https://github.com/octocat/Hello-World/raw/6dcb.../file1.txt",
                        "contents_url": "https://api.github.com/repos/octocat/Hello-World/contents/file1.txt?ref=6dcb...",
                        "patch": "@@ -132,7 +132,7 @@ module Test ...",
                    },
                ],
            )
        return httpx.Response(
            200,
            headers={
                "link": '<https://api.github.com/repos/octo/repo/pulls/123/files?page=2>; rel="next", <https://api.github.com/repos/octo/repo/pulls/123/files?page=2>; rel="last"'
            },
            json=[
                {
                    "sha": "bbcd538c8e72b8c175046e27cc8f907076331401",
                    "filename": "a.txt",
                    "status": "added",
                    "additions": 103,
                    "deletions": 21,
                    "changes": 124,
                    "blob_url": "https://github.com/octocat/Hello-World/blob/6dcb.../file1.txt",
                    "raw_url": "https://github.com/octocat/Hello-World/raw/6dcb.../file1.txt",
                    "contents_url": "https://api.github.com/repos/octocat/Hello-World/contents/file1.txt?ref=6dcb...",
                    "patch": "@@ -132,7 +132,7 @@ module Test ...",
                },
            ],
        )

    settings = GitHubSettings(token=SecretStr("ghp_test"), max_pages=1)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    reader = GitHubPullRequestReader(client, settings)

    changed_files = asyncio.run(reader.read_changed_files("octo", "repo", 123))

    assert seen["auth"] == "Bearer ghp_test"
    assert seen["url"] == "https://api.github.com/repos/octo/repo/pulls/123/files"
    assert len(changed_files.changeset.files) == 1
    assert changed_files.changeset.files[0].path == "a.txt"
    assert len(changed_files.coverage) == 1
    assert changed_files.coverage[0].state == CoverageState.PARTIAL
    assert changed_files.coverage[0].reason != ""


def test_read_metadata_uses_trusted_base_url_and_auth() -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={
                "number": 123,
                "title": "Add feature",
                "body": None,
                "base": {"sha": "base111"},
                "head": {"sha": "head222"},
                "url": "https://api.github.com/repos/octo/repo/pulls/123",
            },
        )

    settings = GitHubSettings(token=SecretStr("ghp_test"))
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    reader = GitHubPullRequestReader(client, settings)

    meta = asyncio.run(reader.read_metadata("octo", "repo", 123))

    assert meta.base_sha == "base111"
    assert meta.head_sha == "head222"
    assert meta.body is None
    assert seen["auth"] == "Bearer ghp_test"
    assert seen["url"] == "https://api.github.com/repos/octo/repo/pulls/123"


def test_read_changed_files_uses_trusted_base_url_and_auth() -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json=[
                {
                    "sha": "bbcd538c8e72b8c175046e27cc8f907076331401",
                    "filename": "file1.txt",
                    "status": "added",
                    "additions": 103,
                    "deletions": 21,
                    "changes": 124,
                    "blob_url": "https://github.com/octocat/Hello-World/blob/6dcb.../file1.txt",
                    "raw_url": "https://github.com/octocat/Hello-World/raw/6dcb.../file1.txt",
                    "contents_url": "https://api.github.com/repos/octocat/Hello-World/contents/file1.txt?ref=6dcb...",
                    "patch": "@@ -132,7 +132,7 @@ module Test ...",
                }
            ],
        )

    settings = GitHubSettings(token=SecretStr("ghp_test"))
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    reader = GitHubPullRequestReader(client, settings)

    changed_files = asyncio.run(reader.read_changed_files("octo", "repo", 123))

    assert seen["auth"] == "Bearer ghp_test"
    assert seen["url"] == "https://api.github.com/repos/octo/repo/pulls/123/files"

    files = changed_files.changeset.files
    assert len(files) == 1
    assert files[0].path == "file1.txt"
    assert files[0].change_type is ChangeType.ADDED
    assert changed_files.coverage == ()


async def _no_sleep(_seconds: float) -> None:
    return None


def _file_page() -> list[dict[str, object]]:
    return [
        {"filename": "file1.txt", "status": "added", "additions": 1, "deletions": 0}
    ]


def test_read_changed_files_retries_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("changeguard.adapters.github_client.asyncio.sleep", _no_sleep)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=_file_page())

    settings = GitHubSettings(token=SecretStr("ghp_test"), max_retries=5)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    reader = GitHubPullRequestReader(client, settings)

    changed_files = asyncio.run(reader.read_changed_files("octo", "repo", 123))

    assert calls["n"] == 3
    assert len(changed_files.changeset.files) == 1
    assert changed_files.changeset.files[0].path == "file1.txt"


def test_read_changed_files_does_not_retry_non_retryable_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("changeguard.adapters.github_client.asyncio.sleep", _no_sleep)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404)

    settings = GitHubSettings(token=SecretStr("ghp_test"), max_retries=5)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    reader = GitHubPullRequestReader(client, settings)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(reader.read_changed_files("octo", "repo", 123))

    assert calls["n"] == 1


def test_read_changed_files_throws_rate_limits_after_max_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("changeguard.adapters.github_client.asyncio.sleep", _no_sleep)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429)

    max_retries = 2
    settings = GitHubSettings(token=SecretStr("ghp_test"), max_retries=max_retries)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    reader = GitHubPullRequestReader(client, settings)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(reader.read_changed_files("octo", "repo", 123))

    assert calls["n"] == max_retries
