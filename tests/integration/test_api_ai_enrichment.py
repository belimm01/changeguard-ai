import asyncio
import json

from fastapi.testclient import TestClient
from pydantic import SecretStr

from changeguard.api.app import create_app
from changeguard.api.models import AnalysisRequest
from changeguard.application.llm import LlmRequest, LlmResult
from changeguard.application.rag import run_rag
from changeguard.config import ApiSettings
from changeguard.domain.content import FileContent, Revision
from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.reports import AnalysisReport, ReportStatus


class CitedAdapter:
    async def complete_structured(self, request: LlmRequest) -> LlmResult:
        source = json.loads(request.input_json)["sources"][0]
        citation = {
            k: source[k]
            for k in (
                "source_id",
                "path",
                "side",
                "commit_sha",
                "blob_sha",
                "start_line",
                "end_line",
            )
        }
        citation["quote"] = "Preserve cursor compatibility."
        return LlmResult(
            "available",
            json.dumps(
                {
                    "advisories": [
                        {
                            "advisory_explanation": "Consider testing existing cursors.",
                            "advisory_severity": "medium",
                            "recommended_tests": ["Reuse an existing cursor."],
                            "migration_considerations": "",
                            "rollback_considerations": "",
                            "citations": [citation],
                        }
                    ]
                }
            ),
        )


def test_api_exposes_validated_advisory_without_replacing_findings() -> None:
    def pipeline(request: AnalysisRequest) -> AnalysisReport:
        report = AnalysisReport(
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
                    "Cursor compatibility",
                    ("api.yaml",),
                ),
            ),
            (),
            (),
        )
        sources = (
            FileContent(
                "head",
                "Preserve cursor compatibility.",
                Revision.HEAD,
                30,
                "docs/api.md",
                "blob",
            ),
        )
        return asyncio.run(run_rag(report, sources, CitedAdapter(), question="cursor"))

    client = TestClient(
        create_app(ApiSettings(secret=SecretStr("test-secret")), pipeline)
    )
    response = client.post(
        "/analyze",
        headers={"X-API-Key": "test-secret"},
        json={
            "owner": "example",
            "repository": "repo",
            "pull_request": 1,
            "base_sha": "base",
            "head_sha": "head",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ai"]["accepted_count"] == 1
    assert body["ai"]["status"] == "available"
    assert body["findings"][0]["level"] == "high"
