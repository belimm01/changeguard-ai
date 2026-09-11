import json
from copy import deepcopy

import pytest

from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.dto.findings import FindingDto
from changeguard.serialization import finding_to_dto, serialize_findings


def finding(
    rule_id: str = "example-rule",
    level: RiskLevel = RiskLevel.LOW,
    summary: str = "Example finding",
    evidence_paths: tuple[str, ...] = ("first.py",),
) -> RiskFinding:
    return RiskFinding(
        rule_id=rule_id,
        level=level,
        summary=summary,
        evidence_paths=evidence_paths,
    )


def test_serializes_empty_findings() -> None:
    assert serialize_findings(()) == ()


def test_serializes_every_field() -> None:
    assert serialize_findings(
        (finding(rule_id="rule-1", summary="Review this change"),)
    ) == (
        {
            "rule_id": "rule-1",
            "level": "low",
            "summary": "Review this change",
            "evidence_paths": ["first.py"],
        },
    )


def test_preserves_finding_order() -> None:
    findings = (
        finding(rule_id="first", evidence_paths=("first.py",)),
        finding(rule_id="second", evidence_paths=("second.py",)),
    )

    result = serialize_findings(findings)

    assert [item["rule_id"] for item in result] == ["first", "second"]
    assert isinstance(result, tuple)


def test_preserves_evidence_path_order() -> None:
    result = serialize_findings((finding(evidence_paths=("z.py", "a.py", "z.py")),))

    assert result[0]["evidence_paths"] == ["z.py", "a.py", "z.py"]


@pytest.mark.parametrize("level", list(RiskLevel))
def test_serializes_all_risk_levels(level: RiskLevel) -> None:
    result = serialize_findings((finding(level=level),))

    assert result[0]["level"] == level.value


def test_serialized_findings_are_json_serializable() -> None:
    payload = serialize_findings((finding(),))

    assert json.loads(json.dumps(payload)) == [
        {
            "rule_id": "example-rule",
            "level": "low",
            "summary": "Example finding",
            "evidence_paths": ["first.py"],
        }
    ]


def test_serialization_does_not_mutate_findings() -> None:
    original = finding(evidence_paths=("first.py", "second.py"))
    snapshot = deepcopy(original)

    serialize_findings((original,))

    assert original == snapshot


def test_maps_one_finding_to_a_frozen_dto() -> None:
    dto = finding_to_dto(finding(level=RiskLevel.HIGH))

    assert isinstance(dto, FindingDto)
    assert dto.level == "high"


