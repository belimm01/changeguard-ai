from dataclasses import dataclass

from changeguard.domain.content import Revision
from changeguard.domain.models import validate_relative_path


@dataclass(frozen=True, slots=True)
class CorpusChunk:
    """A bounded piece of repository text with the provenance needed to cite it."""

    path: str
    side: Revision
    sha: str
    start_line: int
    end_line: int
    text: str
    truncated: bool = False

    def __post_init__(self) -> None:
        validate_relative_path(self.path)
        if not self.sha.strip():
            raise ValueError("sha cannot be empty or whitespace-only")
        if self.start_line < 1:
            raise ValueError("start_line must be greater than 0")
        if self.start_line > self.end_line:
            raise ValueError("start_line must be less than or equal to end_line")
        if not self.text:
            raise ValueError("text cannot be empty")


@dataclass(frozen=True, slots=True)
class CorpusSource:
    """Text of one repository file at one revision, already loaded and SHA-bound."""

    path: str
    side: Revision
    sha: str
    text: str

    def __post_init__(self) -> None:
        validate_relative_path(self.path)
        if not self.sha.strip():
            raise ValueError("sha cannot be empty or whitespace-only")


@dataclass(frozen=True, slots=True)
class Corpus:
    """Chunks selected for retrieval and what was left out to stay within budget."""

    chunks: tuple[CorpusChunk, ...]
    omitted_sources: int = 0

    def __post_init__(self) -> None:
        if self.omitted_sources < 0:
            raise ValueError("omitted_sources cannot be negative")

    @property
    def is_partial(self) -> bool:
        return self.omitted_sources > 0
