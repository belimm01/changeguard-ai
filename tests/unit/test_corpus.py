from typing import Any

import pytest

from changeguard.domain.content import Revision
from changeguard.domain.corpus import Corpus, CorpusChunk, CorpusSource

VALID: dict[str, Any] = {
    "path": "docs/api-pagination.md",
    "side": Revision.HEAD,
    "sha": "abc123",
    "start_line": 1,
    "end_line": 3,
    "text": "Cursor tokens are valid for 24 hours after issue.",
}


def test_corpus_chunk_keeps_provenance() -> None:
    chunk = CorpusChunk(**VALID)

    assert chunk.path == "docs/api-pagination.md"
    assert chunk.side is Revision.HEAD
    assert chunk.sha == "abc123"
    assert (chunk.start_line, chunk.end_line) == (1, 3)
    assert chunk.truncated is False


@pytest.mark.parametrize(
    "override",
    [
        {"path": ""},
        {"path": "../secrets.md"},
        {"sha": " "},
        {"start_line": 0},
        {"start_line": 4, "end_line": 3},
        {"text": ""},
    ],
)
def test_corpus_chunk_rejects_missing_provenance(override: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        CorpusChunk(**(VALID | override))


def test_corpus_source_rejects_missing_sha() -> None:
    with pytest.raises(ValueError):
        CorpusSource(path="docs/api.md", side=Revision.HEAD, sha="", text="x")


def test_corpus_reports_partial_when_sources_were_omitted() -> None:
    assert Corpus(chunks=()).is_partial is False
    assert Corpus(chunks=(), omitted_sources=3).is_partial is True


def test_corpus_rejects_negative_omitted_count() -> None:
    with pytest.raises(ValueError):
        Corpus(chunks=(), omitted_sources=-1)


def test_corpus_chunk_from_source_copies_provenance() -> None:
    source = CorpusSource(
        path="docs/api.md", side=Revision.BASE, sha="abc", text="a\nb\n"
    )

    chunk = CorpusChunk.from_source(source, start_line=2, end_line=2, text="b\n")

    assert chunk == CorpusChunk(
        path="docs/api.md",
        side=Revision.BASE,
        sha="abc",
        start_line=2,
        end_line=2,
        text="b\n",
    )


def test_corpus_is_partial_when_chunks_were_omitted_or_truncated() -> None:
    truncated = CorpusChunk(**(VALID | {"truncated": True}))

    assert Corpus(chunks=(), omitted_chunks=1).is_partial is True
    assert Corpus(chunks=(truncated,)).is_partial is True
    assert Corpus(chunks=(CorpusChunk(**VALID),)).is_partial is False
