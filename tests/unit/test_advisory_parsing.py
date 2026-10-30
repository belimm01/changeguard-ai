import json

import pytest

from changeguard.dto.advisory import (
    AdvisoryAnswer,
    Citation,
    MalformedAdvisoryError,
    parse_advisory,
)

QUOTE = "Cursor tokens are valid for 24 hours after issue."


def citation(start_line: int = 3, end_line: int = 3) -> dict[str, object]:
    return {
        "path": "docs/api-pagination.md",
        "start_line": start_line,
        "end_line": end_line,
        "quote": QUOTE,
    }


def test_parse_advisory_returns_answer_with_citations() -> None:
    raw = json.dumps({"answer": QUOTE, "citations": [citation()]})

    assert parse_advisory(raw) == AdvisoryAnswer(
        answer=QUOTE,
        citations=[
            Citation(
                path="docs/api-pagination.md", start_line=3, end_line=3, quote=QUOTE
            )
        ],
    )


@pytest.mark.parametrize(
    "raw",
    [
        "Sure! Here is the answer...",
        "",
        "[]",
        "{}",
        json.dumps({"answer": QUOTE}),
        json.dumps({"answer": QUOTE, "citations": ["docs/api-pagination.md"]}),
        json.dumps({"answer": QUOTE, "citations": [citation(start_line=0)]}),
        json.dumps({"answer": QUOTE, "citations": [citation(end_line=0)]}),
    ],
    ids=[
        "not-json",
        "empty",
        "array",
        "empty-object",
        "missing-citations",
        "citation-not-object",
        "start-line-zero",
        "end-line-zero",
    ],
)
def test_parse_advisory_rejects_malformed_output(raw: str) -> None:
    with pytest.raises(MalformedAdvisoryError):
        parse_advisory(raw)


def test_parse_advisory_keeps_validation_cause() -> None:
    with pytest.raises(MalformedAdvisoryError) as excinfo:
        parse_advisory("{}")

    assert excinfo.value.__cause__ is not None


def test_advisory_schema_requires_answer_and_citations() -> None:
    schema = AdvisoryAnswer.model_json_schema()

    assert set(schema["required"]) == {"answer", "citations"}
