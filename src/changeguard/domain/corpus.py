import hashlib
import json
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

    @property
    def source_id(self) -> str:
        identity = [
            self.path,
            self.side,
            self.commit_sha,
            self.blob_sha,
            self.start_line,
            self.end_line,
            self.text,
        ]
        return hashlib.sha256(
            json.dumps(identity, ensure_ascii=True).encode()
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class CorpusDiagnostic:
    path: str
    side: Revision | None
    reason: str


@dataclass(frozen=True, slots=True)
class Corpus:
    chunks: tuple[CorpusChunk, ...] = ()
    diagnostics: tuple[CorpusDiagnostic, ...] = ()
    excluded_files: int = 0
    omitted_files: int = 0

    @property
    def partial(self) -> bool:
        return bool(self.diagnostics or self.omitted_files)

    @property
    def total_bytes(self) -> int:
        return sum(len(chunk.text.encode("utf-8")) for chunk in self.chunks)


def source_lines(text: str) -> tuple[str, ...]:
    """Split at LF boundaries used by repository line references, preserving bytes."""
    parts = text.split("\n")
    return tuple(part + "\n" for part in parts[:-1]) + (
        (parts[-1],) if parts[-1] else ()
    )
