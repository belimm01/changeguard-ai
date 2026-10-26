from typing import Any

import pytest

from changeguard.domain.content import Revision
from changeguard.domain.corpus import CorpusChunk

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
