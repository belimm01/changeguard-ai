"""Scoped OpenAPI backward-compatibility rule over base/head content."""

from collections.abc import Mapping
from dataclasses import dataclass

from changeguard.domain.content import FileContent
from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.reports import Coverage, CoverageState
from changeguard.parsing.openapi import parse_openapi

RULE_ID = "openapi-compat"
HTTP_METHODS = ("get", "put", "post", "delete", "patch", "options", "head", "trace")


@dataclass(frozen=True, slots=True)
class OpenApiRuleResult:
    findings: tuple[RiskFinding, ...]
    coverage: tuple[Coverage, ...]


def evaluate_openapi_change(
    path: str, base: FileContent | None, head: FileContent | None
) -> OpenApiRuleResult:
    if base is None or head is None:
        return _partial(path, "missing base or head content")

    parsed_base = parse_openapi(base.text)
    parsed_head = parse_openapi(head.text)
    if parsed_base.document is None:
        return _partial(path, str(parsed_base.problem))
    if parsed_head.document is None:
        return _partial(path, str(parsed_head.problem))

    base_paths = parsed_base.document.get("paths")
    head_paths = parsed_head.document.get("paths")
    if not isinstance(base_paths, Mapping) or not isinstance(head_paths, Mapping):
        return _partial(path, "spec has no comparable paths object")

    findings = _removed_paths(path, base_paths, head_paths) + _removed_operations(
        path, base_paths, head_paths
    )
    coverage = (
        Coverage(
            rule_id=RULE_ID,
            target=path,
            state=CoverageState.SUPPORTED,
            reason="compared paths and operations",
        ),
    )
    return OpenApiRuleResult(findings=findings, coverage=coverage)


def _partial(path: str, reason: str) -> OpenApiRuleResult:
    return OpenApiRuleResult(
        findings=(),
        coverage=(
            Coverage(
                rule_id=RULE_ID,
                target=path,
                state=CoverageState.PARTIAL,
                reason=reason,
            ),
        ),
    )


def _removed_paths(
    path: str,
    base_paths: Mapping[str, object],
    head_paths: Mapping[str, object],
) -> tuple[RiskFinding, ...]:
    return tuple(
        _finding(path, RiskLevel.HIGH, f"removed path {api_path}")
        for api_path in sorted(base_paths.keys() - head_paths.keys())
    )


def _removed_operations(
    path: str,
    base_paths: Mapping[str, object],
    head_paths: Mapping[str, object],
) -> tuple[RiskFinding, ...]:
    findings: list[RiskFinding] = []
    for api_path in sorted(base_paths.keys() & head_paths.keys()):
        base_item = base_paths[api_path]
        head_item = head_paths[api_path]
        if not isinstance(base_item, Mapping) or not isinstance(head_item, Mapping):
            continue
        for method in HTTP_METHODS:
            if method in base_item and method not in head_item:
                findings.append(
                    _finding(
                        path,
                        RiskLevel.MEDIUM,
                        f"removed {method.upper()} {api_path}",
                    )
                )
    return tuple(findings)


def _finding(path: str, level: RiskLevel, summary: str) -> RiskFinding:
    return RiskFinding(
        rule_id=RULE_ID,
        level=level,
        summary=summary,
        evidence_paths=(path,),
    )
