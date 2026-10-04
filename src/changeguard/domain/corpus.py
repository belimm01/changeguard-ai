from dataclasses import dataclass

from changeguard.domain.content import Revision
from changeguard.domain.models import validate_relative_path


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

    def __post_init__(self) -> None:
        validate_relative_path(self.path)
        if not self.blob_sha or not self.blob_sha.strip():
            raise ValueError("blob_sha must be set")
        if not self.commit_sha or not self.commit_sha.strip():
            raise ValueError("commit_sha must be set")
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError("line range must be positive and ordered")
