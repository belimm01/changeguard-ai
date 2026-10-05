from dataclasses import replace

from changeguard.application.retrieval import retrieve_context
from changeguard.domain.content import Revision
from changeguard.domain.corpus import Corpus, CorpusChunk
from changeguard.domain.findings import RiskFinding, RiskLevel


def chunk(path: str, text: str) -> CorpusChunk:
    return CorpusChunk(
        path,
        Revision.HEAD,
        "commit",
        "blob",
        text,
        1,
        len(text.splitlines()),
        "text/plain",
        False,
    )


def test_path_overlap_ranks_schema_context_first() -> None:
    api = chunk("schemas/openapi.yaml", "openapi: 3.1.0\npaths: {}")
    other = chunk("adr/storage.md", "# Storage\nUse PostgreSQL.")
    corpus = Corpus((other, api))
    packet = retrieve_context(corpus, ("api/openapi.yaml",))
    assert packet.items[0].chunk.source_id == api.source_id
    assert packet == retrieve_context(Corpus((api, other)), ("api/openapi.yaml",))


def test_installation_guidance_requires_overlap() -> None:
    guide = chunk("README.md", "# Installation\nUpdate pyproject.toml and run uv sync.")
    unrelated = chunk("docs/history.md", "# History\nProject created in September.")
    finding = RiskFinding(
        "python-dependencies",
        RiskLevel.MEDIUM,
        "Dependency update",
        ("pyproject.toml",),
    )
    packet = retrieve_context(
        Corpus((guide, unrelated)), ("pyproject.toml",), (finding,)
    )
    assert [i.chunk for i in packet.items] == [guide]


def test_no_match_and_empty_are_explicit() -> None:
    assert not retrieve_context(Corpus()).items
    assert not retrieve_context(
        Corpus((chunk("a.md", "oranges"),)), question="apples"
    ).items


def test_budgets_omissions_and_tie_order() -> None:
    chunks = tuple(chunk(f"docs/{i:02}.md", "migration " * 700) for i in range(20))
    packet = retrieve_context(Corpus(chunks), question="migration")
    assert packet.total_bytes <= 24 * 1024
    assert len(packet.items) == 3
    assert packet.omitted_chunks == 17
    assert packet.partial
    assert [i.chunk.path for i in packet.items] == [
        "docs/00.md",
        "docs/01.md",
        "docs/02.md",
    ]
    small = tuple(replace(c, text="migration") for c in chunks)
    assert len(retrieve_context(Corpus(small), question="migration").items) == 12
    assert len(retrieve_context(Corpus(small), ("migration.py",)).items) == 4


def test_fixture_retrieval_accuracy() -> None:
    corpus = Corpus(
        (
            chunk("api/openapi.yaml", "OpenAPI pagination cursor contract"),
            chunk(
                "docs/install.md", "Installation pyproject.toml uv sync dependencies"
            ),
            chunk("adr/storage.md", "PostgreSQL transaction rollback storage"),
        )
    )
    cases = [
        ("pagination", "api/openapi.yaml"),
        ("uv sync", "docs/install.md"),
        ("transaction rollback", "adr/storage.md"),
    ]
    correct = sum(
        retrieve_context(corpus, question=query).items[0].chunk.path == expected
        for query, expected in cases
    )
    accuracy = correct / len(cases)
    assert accuracy == 1.0
