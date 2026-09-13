from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.reports import (
    AnalysisReport,
    Coverage,
    CoverageState,
    Evidence,
    ReportStatus,
)
from changeguard.reporting import derive_status, serialize_report


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
    assert rs.get("status") == "complete"
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
