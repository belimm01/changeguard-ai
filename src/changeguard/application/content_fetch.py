from typing import Protocol

from changeguard.adapters.github_pull_request import PullRequestMetadata
from changeguard.domain.content import RemoteContentResult, Revision
from changeguard.domain.models import ChangeSet, ChangeType
from changeguard.domain.reports import Coverage, CoverageState

_SIDES = {
    ChangeType.ADDED: (Revision.HEAD,),
    ChangeType.DELETED: (Revision.BASE,),
    ChangeType.MODIFIED: (Revision.BASE, Revision.HEAD),
    ChangeType.RENAMED: (Revision.BASE, Revision.HEAD),
}


class ContentReader(Protocol):
    async def get_content(
        self,
        owner: str,
        name: str,
        path: str,
        sha: str,
        ref: Revision,
        remaining_bytes: int | None = None,
    ) -> RemoteContentResult: ...


async def fetch_changed_content(
    metadata: PullRequestMetadata,
    change_set: ChangeSet,
    reader: ContentReader,
    total_bytes: int,
    expected_head_sha: str | None = None,
) -> list[RemoteContentResult]:
    if expected_head_sha is not None and expected_head_sha != metadata.head_sha:
        return [
            RemoteContentResult(
                content=None,
                coverage=(
                    Coverage(
                        rule_id="github-changed-files",
                        target=f"{metadata.owner}/{metadata.name}#{metadata.number}",
                        state=CoverageState.PARTIAL,
                        reason="head sha mismatch",
                    ),
                ),
            )
        ]
    remaining_bytes = total_bytes
    contents: list[RemoteContentResult] = []
    for file in change_set.files:
        for side in _SIDES[file.change_type]:
            sha = metadata.head_sha if side is Revision.HEAD else metadata.base_sha
            remote_content_result = await reader.get_content(
                owner=metadata.owner,
                name=metadata.name,
                path=file.path,
                sha=sha,
                ref=side,
                remaining_bytes=remaining_bytes,
            )
            if remote_content_result.content is not None:
                remaining_bytes -= remote_content_result.content.size

            contents.append(remote_content_result)

    return contents
