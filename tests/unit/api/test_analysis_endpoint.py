from collections.abc import Callable

from fastapi.testclient import TestClient
from pydantic import SecretStr

from changeguard.api.app import create_app
from changeguard.api.models import AnalysisRequest
from changeguard.config import ApiSettings
from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.reports import (
    AnalysisReport,
    Coverage,
    CoverageState,
    ReportStatus,
)

_SECRET = "s3cret-value"


def _settings(max_request_bytes: int = 65_536) -> ApiSettings:
    return ApiSettings(secret=SecretStr(_SECRET), max_request_bytes=max_request_bytes)


def _complete_report() -> AnalysisReport:
    return AnalysisReport(
        analysis_version="1",
        repository="octo/demo",
        pull_request="7",
        base_sha="a" * 40,
        head_sha="b" * 40,
        status=ReportStatus.COMPLETE,
        findings=(
            RiskFinding(
                rule_id="openapi-compat",
                level=RiskLevel.HIGH,
                summary="removed path /orders",
                evidence_paths=("api/openapi.yaml",),
            ),
        ),
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


def _partial_report() -> AnalysisReport:
    return AnalysisReport(
        analysis_version="1",
        repository="octo/demo",
        pull_request="7",
        base_sha=None,
        head_sha=None,
        status=ReportStatus.PARTIAL,
        findings=(),
        evidence=(),
        coverage=(
            Coverage(
                rule_id="openapi-compat",
                target="api/openapi.yaml",
                state=CoverageState.PARTIAL,
                reason="missing base or head content",
            ),
        ),
    )


class _SpyPipeline:
    def __init__(self, report: AnalysisReport | None = None) -> None:
        self.calls: list[AnalysisRequest] = []
        self._report = report or _complete_report()

    def __call__(self, request: AnalysisRequest) -> AnalysisReport:
        self.calls.append(request)
        return self._report


def _client(
    pipeline: Callable[[AnalysisRequest], AnalysisReport],
    max_request_bytes: int = 65_536,
) -> TestClient:
    app = create_app(_settings(max_request_bytes=max_request_bytes), pipeline)
    return TestClient(app)


_VALID_BODY = {
    "owner": "octo",
    "repository": "demo",
    "pull_request": 7,
    "base_sha": "a" * 40,
    "head_sha": "b" * 40,
}


def test_missing_auth_returns_401_and_does_not_run_pipeline() -> None:
    pipeline = _SpyPipeline()
    response = _client(pipeline).post("/analyze", json=_VALID_BODY)
    assert response.status_code == 401
    assert pipeline.calls == []


def test_wrong_secret_returns_403() -> None:
    pipeline = _SpyPipeline()
    response = _client(pipeline).post(
        "/analyze", json=_VALID_BODY, headers={"X-API-Key": "wrong"}
    )
    assert response.status_code == 403
    assert pipeline.calls == []


def test_valid_request_invokes_pipeline_once_and_returns_report() -> None:
    pipeline = _SpyPipeline()
    response = _client(pipeline).post(
        "/analyze", json=_VALID_BODY, headers={"X-API-Key": _SECRET}
    )
    assert response.status_code == 200
    assert len(pipeline.calls) == 1
    body = response.json()
    assert body["schema_version"] == "1"
    assert body["status"] == "complete"
    assert body["findings"][0]["rule_id"] == "openapi-compat"


def test_partial_report_returns_200_with_partial_status() -> None:
    pipeline = _SpyPipeline(_partial_report())
    response = _client(pipeline).post(
        "/analyze", json=_VALID_BODY, headers={"X-API-Key": _SECRET}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "partial"


def test_invalid_input_returns_422() -> None:
    pipeline = _SpyPipeline()
    bad = {**_VALID_BODY, "pull_request": 0, "head_sha": "  "}
    response = _client(pipeline).post(
        "/analyze", json=bad, headers={"X-API-Key": _SECRET}
    )
    assert response.status_code == 422
    assert pipeline.calls == []


def test_oversized_body_returns_413() -> None:
    pipeline = _SpyPipeline()
    response = _client(pipeline, max_request_bytes=10).post(
        "/analyze", json=_VALID_BODY, headers={"X-API-Key": _SECRET}
    )
    assert response.status_code == 413
    assert pipeline.calls == []


def test_unexpected_exception_is_sanitized_500() -> None:
    def boom(request: AnalysisRequest) -> AnalysisReport:
        raise RuntimeError(f"token leak {_SECRET}")

    response = _client(boom).post(
        "/analyze", json=_VALID_BODY, headers={"X-API-Key": _SECRET}
    )
    assert response.status_code == 500
    text = response.text
    assert _SECRET not in text
    assert "Traceback" not in text
    assert "token leak" not in text
    assert response.json()["detail"] == "internal analysis error"
