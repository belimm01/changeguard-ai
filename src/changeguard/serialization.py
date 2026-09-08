"""Map immutable domain findings to a stable JSON-compatible response."""

from changeguard.domain.findings import RiskFinding
from changeguard.dto.findings import FindingDto


def serialize_findings(
    findings: tuple[RiskFinding, ...],
) -> tuple[dict[str, object], ...]:
    return tuple(
        finding_to_dto(finding).model_dump(mode="json") for finding in findings
    )


def finding_to_dto(finding: RiskFinding) -> FindingDto:
    return FindingDto(
        rule_id=finding.rule_id,
        level=finding.level.value,
        summary=finding.summary,
        evidence_paths=list(finding.evidence_paths),
    )
