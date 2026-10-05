from dataclasses import replace
from itertools import pairwise

import pytest

from changeguard.application.corpus import is_corpus_path, split_chunk
from changeguard.domain.content import Revision
from changeguard.domain.corpus import CorpusChunk


def test_markdown_chunk_keeps_sha_and_range() -> None:
    expected_text = "# API\nGET /health\nReturns 200\n"
    corpus = CorpusChunk(
        path="docs/api.md",
        side=Revision.HEAD,
        commit_sha="sha1234",
        blob_sha="blob_sha1234",
        text=expected_text,
        start_line=1,
        end_line=3,
        media_kind="text/markdown",
        truncated=False,
    )

    assert corpus.commit_sha == "sha1234"
    assert corpus.blob_sha == "blob_sha1234"
    assert corpus.path == "docs/api.md"
    assert corpus.side == Revision.HEAD
    assert corpus.start_line == 1
    assert corpus.end_line == 3
    assert corpus.media_kind == "text/markdown"
    assert not corpus.truncated
    assert corpus.text == expected_text


def test_chunk_throws_validation_error() -> None:
    with pytest.raises(ValueError, match="blob_sha must be set"):
        CorpusChunk(
            path="docs/api.md",
            side=Revision.HEAD,
            commit_sha="sha1234",
            text="test",
            blob_sha="    ",
            start_line=1,
            end_line=3,
            media_kind="text/markdown",
            truncated=False,
        )

    with pytest.raises(ValueError, match="commit_sha must be set"):
        CorpusChunk(
            commit_sha="   ",
            path="docs/api.md",
            side=Revision.HEAD,
            text="test",
            blob_sha="blob_sha1234",
            start_line=1,
            end_line=3,
            media_kind="text/markdown",
            truncated=False,
        )


def test_split_chunk_preserves_text_and_ranges() -> None:
    data = CorpusChunk(
        text="line1\nline2\nline3",
        start_line=1,
        end_line=3,
        media_kind="text/markdown",
        truncated=False,
        commit_sha="sha1234",
        blob_sha="blobsha1234",
        path="docs/api.md",
        side=Revision.HEAD,
    )

    result = split_chunk(data, max_lines=2)
    assert len(result) == 2
    assert result[0].text == "line1\nline2\n"
    assert result[0].start_line == 1
    assert "".join(part.text for part in result) == data.text
    assert result[0].end_line == 2
    assert result[1].text == "line3"
    assert result[1].start_line == 3
    assert result[1].end_line == 3


@pytest.fixture
def source_chunk() -> CorpusChunk:
    return CorpusChunk(
        path="docs/api.md",
        side=Revision.BASE,
        commit_sha="fake-commit",
        blob_sha="fake-blob",
        text="one\ntwo\nthree\nfour\n",
        start_line=10,
        end_line=13,
        media_kind="text/markdown",
        truncated=False,
    )


@pytest.mark.parametrize("truncated", [False, True])
@pytest.mark.parametrize("separator", ["\n", "\r\n"])
def test_split_chunk_exact_multiple_preserves_provenance(
    source_chunk: CorpusChunk, truncated: bool, separator: str
) -> None:
    source = replace(
        source_chunk,
        text=source_chunk.text.replace("\n", separator),
        truncated=truncated,
    )
    result = split_chunk(source, 2)
    assert len(result) == 2
    assert [(part.start_line, part.end_line) for part in result] == [(10, 11), (12, 13)]
    assert "".join(part.text for part in result) == source.text
    for part in result:
        assert part.text
        assert part.path == source.path
        assert part.side == source.side
        assert part.commit_sha == source.commit_sha
        assert part.blob_sha == source.blob_sha
        assert part.media_kind == source.media_kind
        assert part.truncated == source.truncated
    assert source.start_line == 10
    assert source.end_line == 13
    assert source.text == source_chunk.text.replace("\n", separator)


@pytest.mark.parametrize("max_lines", [1, 3, 4, 5])
def test_split_chunk_ranges_cover_source(
    source_chunk: CorpusChunk, max_lines: int
) -> None:
    result = split_chunk(source_chunk, max_lines)
    assert "".join(part.text for part in result) == source_chunk.text
    assert result[0].start_line == source_chunk.start_line
    assert result[-1].end_line == source_chunk.end_line
    for part in result:
        assert 1 <= len(part.text.splitlines()) <= max_lines
        assert part.end_line - part.start_line + 1 == len(part.text.splitlines())
    for previous, following in pairwise(result):
        assert following.start_line == previous.end_line + 1


@pytest.mark.parametrize("max_lines", [0, -1])
def test_split_chunk_rejects_nonpositive_limit(
    source_chunk: CorpusChunk, max_lines: int
) -> None:
    with pytest.raises(ValueError, match="max_lines must be positive"):
        split_chunk(source_chunk, max_lines)


def test_split_chunk_empty_text_returns_no_chunks(source_chunk: CorpusChunk) -> None:
    assert split_chunk(replace(source_chunk, text=""), 2) == ()


@pytest.mark.parametrize("max_lines", [2, 10])
def test_split_chunk_rejects_mismatched_range(
    source_chunk: CorpusChunk, max_lines: int
) -> None:
    with pytest.raises(ValueError, match="line range must match text line count"):
        split_chunk(replace(source_chunk, end_line=14), max_lines)


@pytest.mark.parametrize(
    "path", ["", "  ", "/docs/api.md", "../api.md", "docs\\api.md", "a\0b"]
)
def test_chunk_rejects_invalid_path(source_chunk: CorpusChunk, path: str) -> None:
    with pytest.raises(ValueError, match="path"):
        replace(source_chunk, path=path)


@pytest.mark.parametrize("start,end", [(0, 1), (-1, 1), (3, 2)])
def test_chunk_rejects_invalid_range(
    source_chunk: CorpusChunk, start: int, end: int
) -> None:
    with pytest.raises(ValueError, match="line range must be positive and ordered"):
        replace(source_chunk, start_line=start, end_line=end)


@pytest.mark.parametrize("sha", ["", " "])
def test_chunk_rejects_blank_shas(source_chunk: CorpusChunk, sha: str) -> None:
    with pytest.raises(ValueError, match="commit_sha must be set"):
        replace(source_chunk, commit_sha=sha)
    with pytest.raises(ValueError, match="blob_sha must be set"):
        replace(source_chunk, blob_sha=sha)


@pytest.mark.parametrize(
    "path,expected",
    [
        ("README", True),
        ("README.md", True),
        ("README.notes", True),
        ("service/README.md", True),
        ("docs/api.md", True),
        ("docs/guide.txt", True),
        ("adr/decision.txt", True),
        ("docs/adr/decision.md", True),
        ("schema.avsc", True),
        ("schema.yaml", True),
        ("schema.yml", True),
        ("schema.json", True),
        ("guide.rst", True),
        ("notes.md", True),
        ("src/main.py", False),
        ("docs-old/guide.txt", False),
        ("adr-old/decision.txt", False),
        ("building.md", True),
        ("node_modules/readme.md", False),
        ("services/api/node_modules/readme.md", False),
        ("docs/.git/config", False),
        (".git/config", False),
        (".venv/readme.md", False),
        ("dist/api.json", False),
        ("build/api.yaml", False),
        ("docs/build/api.yaml", False),
        ("docs/uv.lock", False),
        ("docs/yarn.lock", False),
        ("docs/package-lock.json", False),
        ("npm-shrinkwrap.json", False),
        ("pnpm-lock.yaml", False),
    ],
)
def test_corpus_path_selection(path: str, expected: bool) -> None:
    assert is_corpus_path(path) is expected
