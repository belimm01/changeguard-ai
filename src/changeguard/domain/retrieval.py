from dataclasses import dataclass

from changeguard.domain.corpus import CorpusChunk


@dataclass(frozen=True, slots=True)
class ContextItem:
    chunk: CorpusChunk
    score: int
    reasons: tuple[str, ...]
    matched_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContextPacket:
    items: tuple[ContextItem, ...] = ()
    omitted_chunks: int = 0
    unmatched_chunks: int = 0
    corpus_partial: bool = False

    @property
    def partial(self) -> bool:
        return self.corpus_partial or self.omitted_chunks > 0

    @property
    def total_bytes(self) -> int:
        return sum(len(item.chunk.text.encode("utf-8")) for item in self.items)
