import json
from io import StringIO
from pathlib import Path

from changeguard.rag import main


def test_demo_selects_relevant_sources_without_calling_model() -> None:
    fixture = Path(__file__).parents[2] / "examples/rag/review.json"
    output = StringIO()
    assert main([], stdin=StringIO(fixture.read_text()), stdout=output) == 0
    result = json.loads(output.getvalue())
    assert [item["path"] for item in result["retrieval"]["selected"]] == [
        "api/openapi.yaml",
        "docs/api-pagination.md",
    ]
    assert result["report"]["ai"]["status"] == "unavailable"
    assert result["report"]["status"] == "partial"
    assert result["report"]["findings"][0]["level"] == "high"


def test_invalid_input_is_safe() -> None:
    error = StringIO()
    assert (
        main(
            [],
            stdin=StringIO('{"private":"do not echo"}'),
            stdout=StringIO(),
            stderr=error,
        )
        == 2
    )
    assert error.getvalue() == "invalid RAG input\n"
