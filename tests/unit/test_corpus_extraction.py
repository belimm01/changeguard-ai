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
    assert corpus.truncated == False
    assert corpus.text == expected_text
