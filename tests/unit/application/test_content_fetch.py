import asyncio
from unittest.mock import AsyncMock

from changeguard.adapters.github_pull_request import PullRequestMetadata
from changeguard.application.content_fetch import fetch_changed_content
from changeguard.domain.content import FileContent, RemoteContentResult, Revision
from changeguard.domain.models import ChangedFile, ChangeSet, ChangeType
from changeguard.domain.reports import Coverage, CoverageState


def test_modified_fetches_base_and_head() -> None:
    reader = AsyncMock()
    reader.get_content.return_value = RemoteContentResult(
        content=FileContent(sha="x", text="x", revision=Revision.HEAD, size=1),
        coverage=(),
    )
    change_set = ChangeSet(
        files=(
            ChangedFile(
                path="m.py", change_type=ChangeType.MODIFIED, additions=1, deletions=1
            ),
        )
    )
    asyncio.run(fetch_changed_content(_meta(), change_set, reader, total_bytes=1000))

    assert reader.get_content.await_count == 2
    reader.get_content.assert_any_await(
        owner="o",
        name="r",
        path="m.py",
        sha="BASE1",
        ref=Revision.BASE,
        remaining_bytes=1000,
    )
    reader.get_content.assert_any_await(
        owner="o",
        name="r",
        path="m.py",
        sha="HEAD1",
        ref=Revision.HEAD,
        remaining_bytes=999,
    )


def test_added_fetches_head_only() -> None:
    reader = AsyncMock()
    reader.get_content.return_value = RemoteContentResult(
        content=FileContent(sha="x", text="x", revision=Revision.HEAD, size=1),
        coverage=(),
    )
    change_set = ChangeSet(
        files=(
            ChangedFile(
                path="new.py", change_type=ChangeType.ADDED, additions=1, deletions=0
            ),
        )
    )
    asyncio.run(fetch_changed_content(_meta(), change_set, reader, total_bytes=1000))

    assert reader.get_content.await_count == 1
    (await_call,) = reader.get_content.await_args_list
    assert await_call.kwargs["ref"] == Revision.HEAD
    assert await_call.kwargs["sha"] == "HEAD1"


def test_deleted_fetches_base_only() -> None:
    reader = AsyncMock()
    reader.get_content.return_value = RemoteContentResult(
        content=FileContent(sha="x", text="x", revision=Revision.BASE, size=1),
        coverage=(),
    )
    change_set = ChangeSet(
        files=(
            ChangedFile(
                path="gone.py", change_type=ChangeType.DELETED, additions=0, deletions=1
            ),
        )
    )
    asyncio.run(fetch_changed_content(_meta(), change_set, reader, total_bytes=1000))

    assert reader.get_content.await_count == 1
    (await_call,) = reader.get_content.await_args_list
    assert await_call.kwargs["ref"] == Revision.BASE
    assert await_call.kwargs["sha"] == "BASE1"


def test_over_budget_yields_partial_for_later_files() -> None:
    def respond(
        *,
        owner: str,
        name: str,
        path: str,
        sha: str,
        ref: Revision,
        remaining_bytes: int | None = None,
    ) -> RemoteContentResult:
        if remaining_bytes is not None and remaining_bytes <= 0:
            return RemoteContentResult(
                content=None,
                coverage=(
                    Coverage(
                        rule_id="github-content",
                        target=path,
                        state=CoverageState.PARTIAL,
                        reason="aggregate content byte limit exceeded",
                    ),
                ),
            )
        return RemoteContentResult(
            content=FileContent(sha=sha, text="x", revision=ref, size=10),
            coverage=(),
        )

    reader = AsyncMock()
    reader.get_content.side_effect = respond
    change_set = ChangeSet(
        files=(
            ChangedFile(
                path="first.py", change_type=ChangeType.ADDED, additions=1, deletions=0
            ),
            ChangedFile(
                path="second.py", change_type=ChangeType.ADDED, additions=1, deletions=0
            ),
        )
    )
    results = asyncio.run(
        fetch_changed_content(_meta(), change_set, reader, total_bytes=5)
    )

    assert results[0].content is not None
    assert results[1].content is None
    assert results[1].coverage[0].state == CoverageState.PARTIAL


def _meta() -> PullRequestMetadata:
    return PullRequestMetadata(
        owner="o",
        name="r",
        number=1,
        base_sha="BASE1",
        head_sha="HEAD1",
        title=None,
        body=None,
        api_url="u",
    )
