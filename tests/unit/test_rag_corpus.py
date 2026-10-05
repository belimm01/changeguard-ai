from dataclasses import replace

import pytest

from changeguard.application.corpus import extract_corpus, truncate_utf8
from changeguard.domain.content import FileContent, Revision


def source(
    path: str = "docs/api.md", text: str = "# API\nA stable contract.\n"
) -> FileContent:
    return FileContent(
        "fake-commit",
        text,
        Revision.HEAD,
        len(text.encode(errors="surrogatepass")),
        path,
        "fake-blob",
    )


@pytest.mark.parametrize(
    "text,limit,expected",
    [
        ("abc", 2, ("ab", True)),
        ("é", 1, ("", True)),
        ("é", 2, ("é", False)),
        ("🙂", 3, ("", True)),
        ("a", 0, ("", True)),
        ("", 0, ("", False)),
    ],
)
def test_truncate_utf8(text: str, limit: int, expected: tuple[str, bool]) -> None:
    assert truncate_utf8(text, limit) == expected


def test_negative_limit() -> None:
    with pytest.raises(ValueError):
        truncate_utf8("x", -1)


def test_corpus_binds_both_revisions_and_distinct_shas() -> None:
    head = source()
    base = replace(
        head, revision=Revision.BASE, sha="base-commit", blob_sha="base-blob"
    )
    result = extract_corpus((head, base))
    assert [c.side for c in result.chunks] == [Revision.BASE, Revision.HEAD]
    assert result.chunks[0].commit_sha == "base-commit"
    assert result.chunks[0].blob_sha == "base-blob"
    assert result.chunks[0].text == base.text
    assert not result.partial
    assert result == extract_corpus((base, head))


def test_file_limit_and_deterministic_order() -> None:
    sources = tuple(source(f"docs/{i:02}.md") for i in range(40))
    corpus = extract_corpus(tuple(reversed(sources)))
    assert len(corpus.chunks) == 32
    assert corpus.omitted_files == 8
    assert corpus.partial
    assert corpus.chunks[0].path == "docs/00.md"


def test_large_multiline_file_splits_losslessly() -> None:
    original = source(text="hello world\n" * 2000)
    corpus = extract_corpus((original,))
    assert "".join(c.text for c in corpus.chunks) == original.text
    assert all(len(c.text.encode()) <= 8192 for c in corpus.chunks)
    assert corpus.chunks[-1].end_line == 2000
    assert not corpus.partial


def test_long_line_keeps_prefix_with_explicit_truncation() -> None:
    corpus = extract_corpus((source(text="é" * 10000 + "\nrest"),))
    assert corpus.total_bytes == 8192
    assert corpus.chunks[0].truncated
    assert corpus.chunks[0].start_line == corpus.chunks[0].end_line == 1
    assert corpus.partial


def test_total_and_chunk_budgets() -> None:
    corpus = extract_corpus(
        tuple(source(f"docs/{i:02}.md", "a\n" * 20000) for i in range(32))
    )
    assert corpus.total_bytes <= 256 * 1024
    assert len(corpus.chunks) <= 128
    assert corpus.partial


def test_malformed_excluded_and_missing_provenance() -> None:
    corpus = extract_corpus(
        (
            source("node_modules/x.md"),
            source(text="a\0b"),
            source("docs/b.md", "\ud800"),
            replace(source("docs/c.md"), blob_sha=None),
        )
    )
    assert not corpus.chunks
    assert corpus.excluded_files == 1
    assert {d.reason for d in corpus.diagnostics} == {
        "binary_content",
        "invalid_utf8",
        "missing_provenance",
    }


def test_repository_line_ranges_ignore_unicode_separators() -> None:
    text = "first\u2028still first\u0085same\nsecond\r\n"
    result = extract_corpus((source(text=text),))
    assert result.chunks[0].end_line == 2
    assert result.chunks[0].text == text


def test_missing_and_invalid_paths_do_not_create_sources() -> None:
    result = extract_corpus(
        (replace(source(), path=None), replace(source(), path="../api.md"))
    )
    assert not result.chunks
    assert len(result.diagnostics) == 2


def test_remote_skipped_content_retains_partial_diagnostic() -> None:
    from changeguard.domain.content import RemoteContentResult
    from changeguard.domain.reports import Coverage, CoverageState

    remote = RemoteContentResult(
        (
            Coverage(
                "github-content", "docs/a.md", CoverageState.PARTIAL, "binary content"
            ),
        )
    )
    corpus = extract_corpus((remote,))
    assert corpus.partial
    assert not corpus.chunks
    assert corpus.diagnostics[0].reason == "upstream_content_unavailable"


def test_conflicting_source_identity_is_rejected_deterministically() -> None:
    original = source()
    conflicting = replace(original, text="Different bytes for the same claimed blob")
    result = extract_corpus((original, conflicting))
    assert not result.chunks
    assert result.diagnostics[0].reason == "conflicting_source"
    assert result == extract_corpus((conflicting, original))
