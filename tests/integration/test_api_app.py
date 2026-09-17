from fastapi.testclient import TestClient
from pydantic import SecretStr

from changeguard.api.app import create_app
from changeguard.api.models import AnalysisRequest
from changeguard.config import ApiSettings
from changeguard.domain.reports import (
    AnalysisReport,
    Coverage,
    CoverageState,
    ReportStatus,
)


def _report(request: AnalysisRequest) -> AnalysisReport:
    return AnalysisReport(
        analysis_version=request.analysis_version,
        repository=f"{request.owner}/{request.repository}",
        pull_request=str(request.pull_request),
        base_sha=request.base_sha,
        head_sha=request.head_sha,
        status=ReportStatus.COMPLETE,
        findings=(),
        evidence=(),
        coverage=(
            Coverage(
                rule_id="openapi-compat",
                target="api/openapi.yaml",
                state=CoverageState.SUPPORTED,
                reason="compared paths",
            ),
        ),
    )


def test_asgi_smoke_round_trip() -> None:
    settings = ApiSettings(secret=SecretStr("smoke-secret"))
    client = TestClient(create_app(settings, _report))
    response = client.post(
        "/analyze",
        json={
            "owner": "octo",
            "repository": "demo",
            "pull_request": 42,
            "base_sha": "c" * 40,
            "head_sha": "d" * 40,
        },
        headers={"X-API-Key": "smoke-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["repository"] == "octo/demo"
    assert body["pull_request"] == "42"
    assert body["status"] == "complete"
