import pytest

from changeguard.application.corpus import chunk_text
from changeguard.domain.content import Revision
from changeguard.domain.corpus import CorpusChunk

PATH = "docs/api.md"
SHA = "abc123"


def chunk(start: int, end: int, text: str, truncated: bool = False) -> CorpusChunk:
    return CorpusChunk(
        path=PATH,
        side=Revision.BASE,
        sha=SHA,
        start_line=start,
        end_line=end,
        text=text,
        truncated=truncated,
    )


def split(text: str, max_bytes: int) -> tuple[CorpusChunk, ...]:
    return chunk_text(
        path=PATH, side=Revision.BASE, sha=SHA, text=text, max_bytes=max_bytes
    )


def test_chunk_text_groups_whole_lines_within_byte_budget() -> None:
    text = "a\nb\nc\n"

    chunks = split(text, max_bytes=4)

    assert chunks == (chunk(1, 2, "a\nb\n"), chunk(3, 3, "c\n"))
    assert "".join(c.text for c in chunks) == text


def test_chunk_text_returns_nothing_for_empty_text() -> None:
    assert split("", max_bytes=4) == ()


def test_chunk_text_keeps_last_line_without_newline() -> None:
    assert split("a\nb", max_bytes=8) == (chunk(1, 2, "a\nb"),)


def test_chunk_text_counts_utf8_bytes_not_characters() -> None:
    # "é\n" is 2 characters but 3 bytes, so two lines do not fit in 4 bytes.
    assert split("é\né\n", max_bytes=4) == (chunk(1, 1, "é\n"), chunk(2, 2, "é\n"))


def test_chunk_text_truncates_single_oversized_line_on_character_boundary() -> None:
    chunks = split("ab\néééé\ncd\n", max_bytes=5)

    assert chunks == (
        chunk(1, 1, "ab\n"),
        chunk(2, 2, "éé", truncated=True),
        chunk(3, 3, "cd\n"),
    )


def test_chunk_text_numbers_lines_by_lf_only() -> None:
    text = "a b\rc\n"

    assert split(text, max_bytes=16) == (chunk(1, 1, text),)


def test_chunk_text_rejects_budget_below_one_character() -> None:
    with pytest.raises(ValueError):
        split("a\n", max_bytes=3)
