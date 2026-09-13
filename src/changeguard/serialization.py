"""Map immutable domain findings to a stable JSON-compatible response."""

from changeguard.domain.findings import RiskFinding
from changeguard.domain.reports import Coverage, Evidence
from changeguard.dto.findings import FindingDto
from changeguard.dto.reports import CoverageDto, EvidenceDto


def serialize_evidence(
    evidences: tuple[Evidence, ...],
) -> tuple[dict[str, object], ...]:
    return tuple(
        evidence_to_dto(evidence).model_dump(mode="json") for evidence in evidences
    )


def serialize_coverage(
    coverages: tuple[Coverage, ...],
) -> tuple[dict[str, object], ...]:
    return tuple(
        coverage_to_dto(coverage).model_dump(mode="json") for coverage in coverages
    )


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


def evidence_to_dto(finding: Evidence) -> EvidenceDto:
    return EvidenceDto(
        path=finding.path,
        start_line=finding.start_line,
        end_line=finding.end_line,
    )


def coverage_to_dto(coverage: Coverage) -> CoverageDto:
    return CoverageDto(
        rule_id=coverage.rule_id,
        target=coverage.target,
        state=coverage.state.value,
        reason=coverage.reason,
    )
