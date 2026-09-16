from typing import Protocol

from changeguard.adapters.github_pull_request import PullRequestMetadata
from changeguard.domain.content import RemoteContentResult, Revision
from changeguard.domain.models import ChangeSet, ChangeType

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
) -> list[RemoteContentResult]:
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
