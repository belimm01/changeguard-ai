import pytest

from changeguard.application.corpus import build_corpus
from changeguard.domain.content import Revision
from changeguard.domain.corpus import CorpusSource


def source(
    path: str, side: Revision = Revision.HEAD, text: str = "line\n"
) -> CorpusSource:
    return CorpusSource(path=path, side=side, sha="abc123", text=text)


def test_build_corpus_keeps_first_sources_in_path_order_and_counts_the_rest() -> None:
    docs = tuple(source(f"docs/doc-{i:02d}.md") for i in reversed(range(40)))

    corpus = build_corpus((*docs, source("src/app.py")))

    assert [chunk.path for chunk in corpus.chunks] == [
        f"docs/doc-{i:02d}.md" for i in range(32)
    ]
    assert corpus.omitted_sources == 8
    assert corpus.is_partial is True


def test_build_corpus_orders_base_before_head_for_the_same_path() -> None:
    corpus = build_corpus(
        (source("docs/api.md", Revision.HEAD), source("docs/api.md", Revision.BASE))
    )

    assert [chunk.side for chunk in corpus.chunks] == [Revision.BASE, Revision.HEAD]
    assert corpus.is_partial is False


def test_build_corpus_ignores_non_corpus_paths_without_marking_partial() -> None:
    corpus = build_corpus((source("src/app.py"), source("docs/api.md")))

    assert [chunk.path for chunk in corpus.chunks] == ["docs/api.md"]
    assert corpus.is_partial is False


def test_build_corpus_omits_chunks_beyond_chunk_budget() -> None:
    docs = tuple(source(f"docs/doc-{i}.md") for i in range(3))

    corpus = build_corpus(docs, max_chunks=2)

    assert len(corpus.chunks) == 2
    assert corpus.omitted_chunks == 1
    assert corpus.is_partial is True


def test_build_corpus_omits_chunks_beyond_total_byte_budget() -> None:
    docs = tuple(source(f"docs/doc-{i}.md", text="12345\n") for i in range(3))

    corpus = build_corpus(docs, max_total_bytes=13)

    assert [chunk.path for chunk in corpus.chunks] == ["docs/doc-0.md", "docs/doc-1.md"]
    assert corpus.omitted_chunks == 1


def test_build_corpus_stops_at_first_chunk_over_byte_budget() -> None:
    big = source("docs/a.md", text="0123456789\n")
    small = source("docs/b.md", text="x\n")

    corpus = build_corpus((small, big), max_total_bytes=5)

    assert corpus.chunks == ()
    assert corpus.omitted_chunks == 2


def test_build_corpus_orders_duplicate_path_and_side_independently_of_input() -> None:
    first = CorpusSource(path="docs/a.md", side=Revision.HEAD, sha="s1", text="a\n")
    second = CorpusSource(path="docs/a.md", side=Revision.HEAD, sha="s2", text="b\n")

    assert build_corpus((first, second)) == build_corpus((second, first))


@pytest.mark.parametrize(
    "budget", [{"max_sources": -1}, {"max_chunks": -1}, {"max_total_bytes": -1}]
)
def test_build_corpus_rejects_negative_budgets(budget: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        build_corpus((source("docs/a.md"),), **budget)
