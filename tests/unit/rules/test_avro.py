import json
from pathlib import Path

from changeguard.domain.content import FileContent, Revision
from changeguard.domain.findings import RiskLevel
from changeguard.domain.reports import CoverageState
from changeguard.rules.avro import (
    COMPATIBILITY,
    RULE_ID,
    AvroRuleResult,
    evaluate_avro_change,
)

_FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "avro"


def _content(name: str, revision: Revision) -> FileContent:
    text = (_FIXTURES / name).read_text()
    return FileContent(sha=name, text=text, revision=revision, size=len(text.encode()))


def _record(fields: list[dict[str, object]], **extra: object) -> str:
    schema: dict[str, object] = {"type": "record", "name": "User", "fields": fields}
    schema.update(extra)
    return json.dumps(schema)


def _inline(text: str, revision: Revision) -> FileContent:
    return FileContent(
        sha=revision.value, text=text, revision=revision, size=len(text.encode())
    )


def _evaluate(base: str, head: str) -> AvroRuleResult:
    return evaluate_avro_change(
        "schemas/user.avsc",
        base=_inline(base, Revision.BASE),
        head=_inline(head, Revision.HEAD),
    )


def test_added_field_without_default_is_incompatible_from_fixtures() -> None:
    result = evaluate_avro_change(
        "schemas/user.avsc",
        base=_content("base.json", Revision.BASE),
        head=_content("head.json", Revision.HEAD),
    )
    high = [f for f in result.findings if f.level is RiskLevel.HIGH]
    assert len(high) == 1
    assert "email" in high[0].summary
    assert COMPATIBILITY in high[0].summary
    assert high[0].rule_id == RULE_ID
    assert high[0].evidence_paths == ("schemas/user.avsc",)


def test_added_field_with_default_is_compatible() -> None:
    base = _record([{"name": "id", "type": "long"}])
    head = _record(
        [
            {"name": "id", "type": "long"},
            {"name": "email", "type": "string", "default": ""},
        ]
    )
    result = _evaluate(base, head)
    assert result.findings == ()
    assert result.coverage[0].state is CoverageState.SUPPORTED


def test_removed_writer_field_is_compatible() -> None:
    base = _record([{"name": "id", "type": "long"}, {"name": "name", "type": "string"}])
    head = _record([{"name": "id", "type": "long"}])
    result = _evaluate(base, head)
    assert result.findings == ()


def test_int_to_long_promotion_is_compatible() -> None:
    base = _record([{"name": "id", "type": "int"}])
    head = _record([{"name": "id", "type": "long"}])
    result = _evaluate(base, head)
    assert result.findings == ()


def test_long_to_int_is_incompatible() -> None:
    base = _record([{"name": "id", "type": "long"}])
    head = _record([{"name": "id", "type": "int"}])
    result = _evaluate(base, head)
    high = [f for f in result.findings if f.level is RiskLevel.HIGH]
    assert len(high) == 1
    assert "id" in high[0].summary
    assert "long -> int" in high[0].summary


def test_full_name_change_is_incompatible() -> None:
    base = _record([{"name": "id", "type": "long"}], namespace="com.old")
    head = _record([{"name": "id", "type": "long"}], namespace="com.new")
    result = _evaluate(base, head)
    high = [f for f in result.findings if f.level is RiskLevel.HIGH]
    assert any("full name" in f.summary for f in high)


def test_union_field_is_unsupported_coverage() -> None:
    base = _record([{"name": "id", "type": ["null", "long"]}])
    head = _record([{"name": "id", "type": ["null", "long"]}])
    result = _evaluate(base, head)
    unsupported = [c for c in result.coverage if c.state is CoverageState.UNSUPPORTED]
    assert any("non-primitive field type" in c.reason for c in unsupported)
    assert result.findings == ()


def test_invalid_json_is_partial_coverage() -> None:
    base = _record([{"name": "id", "type": "long"}])
    result = _evaluate(base, "{not json")
    assert result.findings == ()
    assert result.coverage[0].state is CoverageState.PARTIAL


def test_non_record_schema_is_unsupported() -> None:
    result = _evaluate('"string"', '"string"')
    assert result.findings == ()
    assert result.coverage[0].state is CoverageState.UNSUPPORTED
