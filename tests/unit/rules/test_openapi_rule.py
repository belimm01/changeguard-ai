from pathlib import Path

from changeguard.domain.content import FileContent, Revision
from changeguard.domain.findings import RiskLevel
from changeguard.domain.reports import CoverageState
from changeguard.rules.openapi import (
    RULE_ID,
    OpenApiRuleResult,
    evaluate_openapi_change,
)

_FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "openapi"


def _content(name: str, revision: Revision) -> FileContent:
    text = (_FIXTURES / name).read_text()
    return FileContent(sha=name, text=text, revision=revision, size=len(text.encode()))


def _evaluate() -> OpenApiRuleResult:
    return evaluate_openapi_change(
        "api/openapi.yaml",
        base=_content("base.yaml", Revision.BASE),
        head=_content("head.yaml", Revision.HEAD),
    )


def test_detects_removed_path() -> None:
    result = _evaluate()
    high = [f for f in result.findings if f.level is RiskLevel.HIGH]
    assert len(high) == 1
    assert "/orders" in high[0].summary
    assert high[0].rule_id == RULE_ID
    assert high[0].evidence_paths == ("api/openapi.yaml",)


def test_detects_removed_operation() -> None:
    result = _evaluate()
    medium = [f for f in result.findings if f.level is RiskLevel.MEDIUM]
    assert len(medium) == 1
    assert "DELETE /users" in medium[0].summary


def test_reports_supported_coverage_when_compared() -> None:
    result = _evaluate()
    assert len(result.coverage) == 1
    assert result.coverage[0].state is CoverageState.SUPPORTED


def test_no_findings_and_partial_coverage_when_head_missing() -> None:
    result = evaluate_openapi_change(
        "api/openapi.yaml",
        base=_content("base.yaml", Revision.BASE),
        head=None,
    )
    assert result.findings == ()
    assert len(result.coverage) == 1
    assert result.coverage[0].state is CoverageState.PARTIAL


def test_partial_coverage_when_spec_unparseable() -> None:
    bad = FileContent(sha="bad", text="swagger: '2.0'", revision=Revision.HEAD, size=13)
    result = evaluate_openapi_change(
        "api/openapi.yaml",
        base=_content("base.yaml", Revision.BASE),
        head=bad,
    )
    assert result.findings == ()
    assert result.coverage[0].state is CoverageState.PARTIAL
