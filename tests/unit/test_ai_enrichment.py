import asyncio
import json

import pytest

from changeguard.application.llm import LlmRequest, LlmResult
from changeguard.application.rag import run_rag
from changeguard.domain.ai_output import AiStatus
from changeguard.domain.content import FileContent, Revision
from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.reports import AnalysisReport, ReportStatus
from changeguard.reporting import serialize_report


def report() -> AnalysisReport:
    return AnalysisReport(
        "1",
        "example/repo",
        "1",
        "base",
        "head",
        ReportStatus.COMPLETE,
        (
            RiskFinding(
                "api-contract",
                RiskLevel.HIGH,
                "Review pagination compatibility",
                ("openapi.yaml",),
            ),
        ),
        (),
        (),
    )


def sources() -> tuple[FileContent, ...]:
    text = "# API\nClients use cursor pagination.\n"
    return (
        FileContent(
            "head", text, Revision.HEAD, len(text.encode()), "docs/api.md", "blob"
        ),
    )


class FakeLlm:
    def __init__(self, fabricate: bool = False) -> None:
        self.fabricate = fabricate
        self.seen: LlmRequest | None = None

    async def complete_structured(self, request: LlmRequest) -> LlmResult:
        self.seen = request
        source = json.loads(request.input_json)["sources"][0]
        citation = {
            key: source[key]
            for key in (
                "source_id",
                "path",
                "side",
                "commit_sha",
                "blob_sha",
                "start_line",
                "end_line",
            )
        }
        citation["quote"] = "Clients use cursor pagination."
        if self.fabricate:
            citation["source_id"] = "invented"
        return LlmResult(
            "available",
            json.dumps(
                {
                    "advisories": [
                        {
                            "advisory_explanation": "Consider checking pagination compatibility.",
                            "advisory_severity": "low",
                            "recommended_tests": ["Test cursor pagination."],
                            "migration_considerations": "",
                            "rollback_considerations": "",
                            "citations": [citation],
                        }
                    ]
                }
            ),
        )


def test_disabled_ai_preserves_deterministic_findings_with_status() -> None:
    original = report()
    enriched = asyncio.run(run_rag(original, sources(), question="cursor pagination"))
    assert enriched.findings == original.findings
    assert enriched.ai is not None and enriched.ai.status is AiStatus.UNAVAILABLE
    assert enriched.ai.reason == "disabled"


def test_end_to_end_context_generation_validation_preserves_findings() -> None:
    adapter = FakeLlm()
    original = report()
    enriched = asyncio.run(
        run_rag(
            original, sources(), adapter, question="cursor pagination", model="fake"
        )
    )
    assert enriched.findings == original.findings
    assert enriched.ai is not None and enriched.ai.accepted_count == 1
    assert enriched.ai.status is AiStatus.AVAILABLE
    assert adapter.seen is not None
    assert json.loads(adapter.seen.input_json)["sources"][0]["blob_sha"] == "blob"
    assert "ai" in serialize_report(enriched)
    assert original.ai is None


def test_fabricated_evidence_never_replaces_findings() -> None:
    original = report()
    enriched = asyncio.run(
        run_rag(original, sources(), FakeLlm(True), question="pagination")
    )
    assert enriched.findings == original.findings
    assert enriched.ai is not None and enriched.ai.rejected_count == 1
    assert not enriched.ai.advisories


def test_environment_is_not_part_of_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRIVATE_TEST_VALUE", "do-not-send-this-fixture-value")
    adapter = FakeLlm()
    asyncio.run(run_rag(report(), sources(), adapter, question="pagination"))
    assert adapter.seen is not None
    assert "do-not-send-this-fixture-value" not in adapter.seen.input_json
    assert set(json.loads(adapter.seen.input_json)) == {
        "question",
        "findings",
        "sources",
    }


def test_wrong_report_revision_is_not_sent_to_model() -> None:
    from dataclasses import replace

    original = report()
    adapter = FakeLlm()
    wrong = tuple(replace(s, sha="different-head") for s in sources())
    enriched = asyncio.run(run_rag(original, wrong, adapter, question="pagination"))
    assert adapter.seen is None
    assert enriched.ai is not None
    assert enriched.ai.status is AiStatus.NO_CONTEXT
    assert enriched.ai.context_partial
    assert enriched.findings == original.findings


def test_wrong_base_revision_is_not_sent_to_model() -> None:
    from dataclasses import replace

    adapter = FakeLlm()
    wrong = tuple(
        replace(s, sha="different-base", revision=Revision.BASE) for s in sources()
    )
    enriched = asyncio.run(run_rag(report(), wrong, adapter, question="pagination"))
    assert adapter.seen is None
    assert enriched.ai is not None and enriched.ai.context_partial
