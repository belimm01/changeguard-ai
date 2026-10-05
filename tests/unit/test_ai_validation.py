import json
from dataclasses import asdict

import pytest

from changeguard.application.ai_validation import validate_ai_output
from changeguard.domain.ai_output import AiStatus
from changeguard.domain.content import Revision
from changeguard.domain.corpus import CorpusChunk
from changeguard.domain.retrieval import ContextItem, ContextPacket


def context() -> ContextPacket:
    source = CorpusChunk(
        "docs/api.md",
        Revision.HEAD,
        "commit",
        "blob",
        "# API\nClients use cursor pagination.\n",
        10,
        11,
        "text/markdown",
        False,
    )
    return ContextPacket((ContextItem(source, 1, ("text_overlap",), ()),))


def output() -> dict[str, object]:
    chunk = context().items[0].chunk
    citation = {
        "source_id": chunk.source_id,
        "path": chunk.path,
        "side": chunk.side,
        "commit_sha": chunk.commit_sha,
        "blob_sha": chunk.blob_sha,
        "start_line": 11,
        "end_line": 11,
        "quote": "Clients use cursor pagination.",
    }
    return {
        "advisories": [
            {
                "advisory_explanation": "Consider checking cursor compatibility.",
                "advisory_severity": "medium",
                "recommended_tests": ["Test cursor pagination."],
                "migration_considerations": "",
                "rollback_considerations": "",
                "citations": [citation],
            }
        ]
    }


def test_accepts_source_backed_advisory() -> None:
    result = validate_ai_output(json.dumps(output()), context())
    assert result.status is AiStatus.AVAILABLE
    assert result.accepted_count == 1
    assert result.rejected_count == 0


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("source_id", "invented", "unknown_source"),
        ("blob_sha", "wrong", "provenance_mismatch"),
        ("commit_sha", "wrong", "provenance_mismatch"),
        ("side", "base", "provenance_mismatch"),
        ("path", "docs/other.md", "provenance_mismatch"),
        ("start_line", 9, "range_mismatch"),
        ("end_line", 12, "range_mismatch"),
        ("quote", "invented quote", "quote_mismatch"),
    ],
)
def test_rejects_fabricated_citations(field: str, value: object, reason: str) -> None:
    payload = json.loads(json.dumps(output()))
    payload["advisories"][0]["citations"][0][field] = value
    result = validate_ai_output(json.dumps(payload), context())
    assert result.rejected_reasons == (reason,)
    assert not result.advisories


def test_quote_must_be_in_cited_range() -> None:
    payload = json.loads(json.dumps(output()))
    payload["advisories"][0]["citations"][0]["start_line"] = 10
    payload["advisories"][0]["citations"][0]["end_line"] = 10
    assert validate_ai_output(json.dumps(payload), context()).rejected_reasons == (
        "quote_mismatch",
    )


@pytest.mark.parametrize(
    "field,value",
    [("advisory_severity", "critical"), ("citations", []), ("severity", "low")],
)
def test_invalid_schema_is_rejected(field: str, value: object) -> None:
    payload = json.loads(json.dumps(output()))
    payload["advisories"][0][field] = value
    assert validate_ai_output(json.dumps(payload), context()).status is AiStatus.INVALID


def test_mixed_and_confirmed_language_counts() -> None:
    payload = json.loads(json.dumps(output()))
    other = dict(
        payload["advisories"][0], advisory_explanation="This will break all clients."
    )
    payload["advisories"].append(other)
    result = validate_ai_output(json.dumps(payload), context())
    assert (result.accepted_count, result.rejected_count) == (1, 1)
    assert result.status is AiStatus.PARTIAL
    assert "will break" not in json.dumps(asdict(result))
