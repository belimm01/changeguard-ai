from dataclasses import dataclass

from changeguard.domain.content import Revision


@dataclass(frozen=True, slots=True)
class CorpusChunk:
    path: str
    side: Revision
    commit_sha: str
    blob_sha: str
    text: str
    start_line: int
    end_line: int
    media_kind: str
    truncated: bool
