"""Scoped OpenAPI backward-compatibility rule over base/head content."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from changeguard.domain.content import FileContent
from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.reports import Coverage, CoverageState
from changeguard.parsing.openapi import ParsedSpec, SpecProblem, parse_openapi

RULE_ID = "openapi-compat"
HTTP_METHODS = ("get", "put", "post", "delete", "patch", "options", "head", "trace")

# SpecProblem values that describe an unsupported spec dialect rather than a
# transient input problem. These become UNSUPPORTED coverage, not PARTIAL.
_UNSUPPORTED_PROBLEMS = frozenset(
    {SpecProblem.SWAGGER_2, SpecProblem.UNSUPPORTED_VERSION}
)

_MAX_FEATURE_SCAN_NODES = 5_000


@dataclass(frozen=True, slots=True)
class OpenApiRuleResult:
    findings: tuple[RiskFinding, ...]
    coverage: tuple[Coverage, ...]


def evaluate_openapi_change(
    path: str, base: FileContent | None, head: FileContent | None
) -> OpenApiRuleResult:
    if base is None or head is None:
        return _coverage_only(
            path, CoverageState.PARTIAL, "missing base or head content"
        )

    parsed_base = parse_openapi(base.text)
    parsed_head = parse_openapi(head.text)
    for parsed in (parsed_base, parsed_head):
        if parsed.document is None:
            return _coverage_only(path, *_problem_coverage(parsed))

    assert parsed_base.document is not None
    assert parsed_head.document is not None

    base_paths = parsed_base.document.get("paths")
    head_paths = parsed_head.document.get("paths")
    if not isinstance(base_paths, Mapping) or not isinstance(head_paths, Mapping):
        return _coverage_only(
            path, CoverageState.PARTIAL, "spec has no comparable paths object"
        )

    findings = (
        _removed_paths(path, base_paths, head_paths)
        + _removed_operations(path, base_paths, head_paths)
        + _removed_responses(path, base_paths, head_paths)
        + _added_required_parameters(path, base_paths, head_paths)
    )
    coverage = (
        Coverage(
            rule_id=RULE_ID,
            target=path,
            state=CoverageState.SUPPORTED,
            reason="compared paths, operations, responses and required parameters",
        ),
    ) + _unsupported_features(path, parsed_head.document)
    return OpenApiRuleResult(findings=findings, coverage=coverage)


def _problem_coverage(parsed: ParsedSpec) -> tuple[CoverageState, str]:
    if parsed.problem in _UNSUPPORTED_PROBLEMS:
        return CoverageState.UNSUPPORTED, str(parsed.problem)
    return CoverageState.PARTIAL, str(parsed.problem)


def _coverage_only(path: str, state: CoverageState, reason: str) -> OpenApiRuleResult:
    return OpenApiRuleResult(
        findings=(),
        coverage=(Coverage(rule_id=RULE_ID, target=path, state=state, reason=reason),),
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


def _removed_responses(
    path: str,
    base_paths: Mapping[str, object],
    head_paths: Mapping[str, object],
) -> tuple[RiskFinding, ...]:
    findings: list[RiskFinding] = []
    for api_path, method, base_op, head_op in _iter_common_operations(
        base_paths, head_paths
    ):
        base_responses = base_op.get("responses")
        head_responses = head_op.get("responses")
        if not isinstance(base_responses, Mapping) or not isinstance(
            head_responses, Mapping
        ):
            continue
        for code in sorted(base_responses.keys() - head_responses.keys()):
            findings.append(
                _finding(
                    path,
                    RiskLevel.MEDIUM,
                    f"removed response {code} from {method.upper()} {api_path}",
                )
            )
    return tuple(findings)


def _added_required_parameters(
    path: str,
    base_paths: Mapping[str, object],
    head_paths: Mapping[str, object],
) -> tuple[RiskFinding, ...]:
    findings: list[RiskFinding] = []
    for api_path, method, base_op, head_op in _iter_common_operations(
        base_paths, head_paths
    ):
        added = _required_parameters(head_op) - _required_parameters(base_op)
        for name, location in sorted(added):
            findings.append(
                _finding(
                    path,
                    RiskLevel.HIGH,
                    f"added required parameter {name} ({location}) "
                    f"to {method.upper()} {api_path}",
                )
            )
    return tuple(findings)


def _required_parameters(operation: Mapping[str, object]) -> set[tuple[str, str]]:
    raw = operation.get("parameters")
    if not isinstance(raw, list):
        return set()
    required: set[tuple[str, str]] = set()
    for parameter in raw:
        if not isinstance(parameter, Mapping):
            continue
        name = parameter.get("name")
        location = parameter.get("in")
        if not isinstance(name, str) or not isinstance(location, str):
            continue
        # Path parameters are required by definition; treat them and any
        # explicitly required parameter as breaking when newly introduced.
        if parameter.get("required") is True or location == "path":
            required.add((name, location))
    return required


def _iter_common_operations(
    base_paths: Mapping[str, object],
    head_paths: Mapping[str, object],
) -> Iterator[tuple[str, str, Mapping[str, object], Mapping[str, object]]]:
    for api_path in sorted(base_paths.keys() & head_paths.keys()):
        base_item = base_paths[api_path]
        head_item = head_paths[api_path]
        if not isinstance(base_item, Mapping) or not isinstance(head_item, Mapping):
            continue
        for method in HTTP_METHODS:
            base_op = base_item.get(method)
            head_op = head_item.get(method)
            if isinstance(base_op, Mapping) and isinstance(head_op, Mapping):
                yield api_path, method, base_op, head_op


def _unsupported_features(
    path: str, document: Mapping[str, object]
) -> tuple[Coverage, ...]:
    found = _scan_features(document)
    return tuple(
        Coverage(
            rule_id=RULE_ID,
            target=path,
            state=CoverageState.UNSUPPORTED,
            reason=f"unsupported OpenAPI feature not evaluated: {feature}",
        )
        for feature in sorted(found)
    )


def _scan_features(document: Mapping[str, object]) -> set[str]:
    # Bounded, non-resolving walk that only records which unsupported constructs
    # appear so they surface as coverage. It never dereferences $ref graphs.
    unsupported_keys = {
        "$ref": "remote or local $ref graph",
        "callbacks": "callbacks",
        "webhooks": "webhooks",
        "links": "links",
        "allOf": "composed schema (allOf)",
        "oneOf": "composed schema (oneOf)",
        "anyOf": "composed schema (anyOf)",
        "discriminator": "discriminator",
    }
    found: set[str] = set()
    stack: list[object] = [document]
    visited = 0
    while stack and visited < _MAX_FEATURE_SCAN_NODES:
        node = stack.pop()
        visited += 1
        if isinstance(node, Mapping):
            for key, value in node.items():
                if isinstance(key, str) and key in unsupported_keys:
                    found.add(unsupported_keys[key])
                stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)
    return found


def _finding(path: str, level: RiskLevel, summary: str) -> RiskFinding:
    return RiskFinding(
        rule_id=RULE_ID,
        level=level,
        summary=summary,
        evidence_paths=(path,),
    )
