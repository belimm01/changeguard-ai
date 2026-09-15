import json

import pytest

from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.reports import (
    AnalysisReport,
    Coverage,
    CoverageState,
    Evidence,
    ReportStatus,
)
from changeguard.reporting import derive_status, serialize_report


def test_report_key_order() -> None:
    report = AnalysisReport(
        findings=(),
        evidence=(),
        coverage=(),
        status=ReportStatus.COMPLETE,
        analysis_version="0.0.0",
        repository="example/repo",
        pull_request="123",
        base_sha="abc123",
        head_sha="def456",
    )
    assert list(serialize_report(report).keys()) == [
        "schema_version",
        "analysis_version",
        "repository",
        "pull_request",
        "base_sha",
        "head_sha",
        "status",
        "findings",
        "evidence",
        "coverage",
    ]


def test_reporting() -> None:
    report = AnalysisReport(
        findings=(
            RiskFinding(
                rule_id="example-rule",
                level=RiskLevel.MEDIUM,
                summary="Example finding",
                evidence_paths=("first.py",),
            ),
        ),
        evidence=(
            Evidence(
                path="first.py",
                start_line=1,
                end_line=2,
            ),
        ),
        coverage=(
            Coverage(
                rule_id="example-rule",
                target="example.py",
                state=CoverageState.PARTIAL,
                reason="Example reason",
            ),
        ),
        status=ReportStatus.COMPLETE,
        analysis_version="0.0.0",
        repository="example/repo",
        pull_request="123",
        base_sha="abc123",
        head_sha="def456",
    )
    rs = serialize_report(report)
    assert rs.get("status") == "partial"
    assert rs.get("analysis_version") == "0.0.0"
    assert rs.get("repository") == "example/repo"
    assert rs.get("pull_request") == "123"
    assert rs.get("base_sha") == "abc123"
    assert rs.get("head_sha") == "def456"
    assert rs.get("schema_version") == "1"
    assert rs["findings"] == [
        {
            "rule_id": "example-rule",
            "level": "medium",
            "summary": "Example finding",
            "evidence_paths": ["first.py"],
        }
    ]
    assert rs["coverage"] == [
        {
            "rule_id": "example-rule",
            "target": "example.py",
            "state": "partial",
            "reason": "Example reason",
        }
    ]


def test_derive_status() -> None:
    assert (
        derive_status(
            (
                Coverage(
                    rule_id="example-rule",
                    target="example.py",
                    state=CoverageState.PARTIAL,
                    reason="Example reason",
                ),
                Coverage(
                    rule_id="example-rule",
                    target="example.py",
                    state=CoverageState.SUPPORTED,
                    reason="Example reason",
                ),
                Coverage(
                    rule_id="example-rule",
                    target="example.py",
                    state=CoverageState.UNSUPPORTED,
                    reason="Example reason",
                ),
            )
        )
        is ReportStatus.UNSUPPORTED
    )
    assert (
        derive_status(
            (
                Coverage(
                    rule_id="example-rule",
                    target="example.py",
                    state=CoverageState.PARTIAL,
                    reason="Example reason",
                ),
                Coverage(
                    rule_id="example-rule",
                    target="example.py",
                    state=CoverageState.SUPPORTED,
                    reason="Example reason",
                ),
                Coverage(
                    rule_id="example-rule",
                    target="example.py",
                    state=CoverageState.SUPPORTED,
                    reason="Example reason",
                ),
            )
        )
        is ReportStatus.PARTIAL
    )
    assert (
        derive_status(
            (
                Coverage(
                    rule_id="example-rule",
                    target="example.py",
                    state=CoverageState.SUPPORTED,
                    reason="Example reason",
                ),
                Coverage(
                    rule_id="example-rule",
                    target="example.py",
                    state=CoverageState.SUPPORTED,
                    reason="Example reason",
                ),
                Coverage(
                    rule_id="example-rule",
                    target="example.py",
                    state=CoverageState.SUPPORTED,
                    reason="Example reason",
                ),
            )
        )
        is ReportStatus.COMPLETE
    )


def _report(**overrides: object) -> AnalysisReport:
    defaults: dict[str, object] = {
        "findings": (),
        "evidence": (),
        "coverage": (),
        "status": ReportStatus.COMPLETE,
        "analysis_version": "0.0.0",
        "repository": "example/repo",
        "pull_request": "123",
        "base_sha": "abc123",
        "head_sha": "def456",
    }
    defaults.update(overrides)
    return AnalysisReport(**defaults)  # type: ignore[arg-type]


def test_complete_report_requires_base_sha() -> None:
    with pytest.raises(ValueError, match="base_sha"):
        _report(status=ReportStatus.COMPLETE, base_sha=None)


def test_complete_report_requires_head_sha() -> None:
    with pytest.raises(ValueError, match="head_sha"):
        _report(status=ReportStatus.COMPLETE, head_sha=None)


def test_partial_report_allows_missing_shas() -> None:
    report = _report(status=ReportStatus.PARTIAL, base_sha=None, head_sha=None)

    assert report.base_sha is None
    assert report.head_sha is None


def test_shas_are_serialized_exactly_as_supplied() -> None:
    rs = serialize_report(_report(base_sha="  spaced  ", head_sha="MiXeD"))

    assert rs["base_sha"] == "  spaced  "
    assert rs["head_sha"] == "MiXeD"


def test_serialized_report_round_trips_through_json() -> None:
    rs = serialize_report(_report())

    assert json.loads(json.dumps(rs)) == rs


def test_evidence_rejects_parent_traversal() -> None:
    with pytest.raises(ValueError, match=r"\.\."):
        Evidence(path="../secret.txt")


def test_evidence_rejects_end_before_start() -> None:
    with pytest.raises(ValueError, match="end_line"):
        Evidence(path="a.py", start_line=5, end_line=2)


def test_evidence_allows_path_without_line_range() -> None:
    evidence = Evidence(path="src/app.py")

    assert evidence.start_line is None
    assert evidence.end_line is None
