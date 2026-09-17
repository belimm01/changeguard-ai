"""Scoped Avro BACKWARD-compatibility rule over base/head schema content.

The head schema is the reader and the base schema is the writer: this checks
whether new consumers can read previously written data. It does not infer
deployment order or promise forward/full compatibility, and it never contacts a
schema registry.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from changeguard.domain.content import FileContent
from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.reports import Coverage, CoverageState
from changeguard.parsing.avro import parse_avro

RULE_ID = "avro-compat"
COMPATIBILITY = "BACKWARD"

_PRIMITIVES = frozenset(
    {"null", "boolean", "int", "long", "float", "double", "bytes", "string"}
)
# Writer type -> reader types it resolves to (Avro primitive promotions).
_PROMOTIONS: dict[str, frozenset[str]] = {
    "int": frozenset({"long", "float", "double"}),
    "long": frozenset({"float", "double"}),
    "float": frozenset({"double"}),
    "string": frozenset({"bytes"}),
    "bytes": frozenset({"string"}),
}


@dataclass(frozen=True, slots=True)
class AvroRuleResult:
    findings: tuple[RiskFinding, ...]
    coverage: tuple[Coverage, ...]


def evaluate_avro_change(
    path: str, base: FileContent | None, head: FileContent | None
) -> AvroRuleResult:
    if base is None or head is None:
        return _coverage_only(
            path, CoverageState.PARTIAL, "missing base or head content"
        )

    parsed_base = parse_avro(base.text)
    parsed_head = parse_avro(head.text)
    for parsed in (parsed_base, parsed_head):
        if parsed.schema is None:
            return _coverage_only(path, CoverageState.PARTIAL, str(parsed.problem))

    base_schema = parsed_base.schema
    head_schema = parsed_head.schema
    if not _is_record(base_schema) or not _is_record(head_schema):
        return _coverage_only(
            path,
            CoverageState.UNSUPPORTED,
            f"only Avro record schemas are evaluated for {COMPATIBILITY} compatibility",
        )
    assert isinstance(base_schema, Mapping)
    assert isinstance(head_schema, Mapping)

    findings: list[RiskFinding] = []
    unsupported: set[str] = set()

    findings.extend(_full_name_change(path, base_schema, head_schema))
    _collect_aliases(base_schema, head_schema, unsupported)

    base_fields = _field_map(base_schema)
    head_fields = _field_map(head_schema)

    findings.extend(_added_reader_fields(path, base_fields, head_fields))
    findings.extend(
        _incompatible_common_fields(path, base_fields, head_fields, unsupported)
    )

    coverage = (
        Coverage(
            rule_id=RULE_ID,
            target=path,
            state=CoverageState.SUPPORTED,
            reason=f"compared record fields for {COMPATIBILITY} compatibility",
        ),
    ) + tuple(
        Coverage(
            rule_id=RULE_ID,
            target=path,
            state=CoverageState.UNSUPPORTED,
            reason=f"unsupported Avro construct not evaluated: {construct}",
        )
        for construct in sorted(unsupported)
    )
    return AvroRuleResult(findings=tuple(findings), coverage=coverage)


def _coverage_only(path: str, state: CoverageState, reason: str) -> AvroRuleResult:
    return AvroRuleResult(
        findings=(),
        coverage=(Coverage(rule_id=RULE_ID, target=path, state=state, reason=reason),),
    )


def _is_record(schema: object) -> bool:
    return (
        isinstance(schema, Mapping)
        and schema.get("type") == "record"
        and isinstance(schema.get("fields"), list)
    )


def _full_name(schema: Mapping[str, object]) -> str:
    name = schema.get("name")
    namespace = schema.get("namespace")
    name_str = name if isinstance(name, str) else ""
    if isinstance(namespace, str) and namespace:
        return f"{namespace}.{name_str}"
    return name_str


def _full_name_change(
    path: str, base: Mapping[str, object], head: Mapping[str, object]
) -> tuple[RiskFinding, ...]:
    base_name = _full_name(base)
    head_name = _full_name(head)
    if base_name and head_name and base_name != head_name:
        return (
            _finding(
                path,
                RiskLevel.HIGH,
                f"record full name changed from {base_name} to {head_name} "
                f"({COMPATIBILITY})",
            ),
        )
    return ()


def _collect_aliases(
    base: Mapping[str, object], head: Mapping[str, object], unsupported: set[str]
) -> None:
    if isinstance(base.get("aliases"), list) or isinstance(head.get("aliases"), list):
        unsupported.add("aliases")


def _field_map(schema: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    fields = schema.get("fields")
    result: dict[str, Mapping[str, object]] = {}
    if not isinstance(fields, list):
        return result
    for field in fields:
        if isinstance(field, Mapping):
            name = field.get("name")
            if isinstance(name, str):
                result[name] = field
    return result


def _added_reader_fields(
    path: str,
    base_fields: Mapping[str, Mapping[str, object]],
    head_fields: Mapping[str, Mapping[str, object]],
) -> tuple[RiskFinding, ...]:
    findings: list[RiskFinding] = []
    for name in sorted(head_fields.keys() - base_fields.keys()):
        if "default" not in head_fields[name]:
            findings.append(
                _finding(
                    path,
                    RiskLevel.HIGH,
                    f"added reader field {name} without a default ({COMPATIBILITY})",
                )
            )
    return tuple(findings)


def _incompatible_common_fields(
    path: str,
    base_fields: Mapping[str, Mapping[str, object]],
    head_fields: Mapping[str, Mapping[str, object]],
    unsupported: set[str],
) -> tuple[RiskFinding, ...]:
    findings: list[RiskFinding] = []
    for name in sorted(base_fields.keys() & head_fields.keys()):
        writer_type = base_fields[name].get("type")
        reader_type = head_fields[name].get("type")
        if not isinstance(writer_type, str) or writer_type not in _PRIMITIVES:
            unsupported.add(f"non-primitive field type ({name})")
            continue
        if not isinstance(reader_type, str) or reader_type not in _PRIMITIVES:
            unsupported.add(f"non-primitive field type ({name})")
            continue
        if not _resolves(writer_type, reader_type):
            findings.append(
                _finding(
                    path,
                    RiskLevel.HIGH,
                    f"incompatible type change for field {name}: "
                    f"{writer_type} -> {reader_type} ({COMPATIBILITY})",
                )
            )
    return tuple(findings)


def _resolves(writer_type: str, reader_type: str) -> bool:
    if writer_type == reader_type:
        return True
    return reader_type in _PROMOTIONS.get(writer_type, frozenset())


def _finding(path: str, level: RiskLevel, summary: str) -> RiskFinding:
    return RiskFinding(
        rule_id=RULE_ID,
        level=level,
        summary=summary,
        evidence_paths=(path,),
    )
