from changeguard.domain.reports import AnalysisReport
from changeguard.dto.reports import AnalysisReportDto
from changeguard.serialization import (
    coverage_to_dto,
    evidence_to_dto,
    finding_to_dto,
)

SCHEMA_VERSION = "1"


def serialize_report(report: AnalysisReport) -> dict[str, object]:
    dto = AnalysisReportDto(
        schema_version=SCHEMA_VERSION,
        findings=[finding_to_dto(finding) for finding in report.findings],
        evidence=[evidence_to_dto(evidence) for evidence in report.evidence],
        coverage=[coverage_to_dto(coverage) for coverage in report.coverage],
        status=report.status,
        analysis_version=report.analysis_version,
        repository=report.repository,
        pull_request=report.pull_request,
        base_sha=report.base_sha,
        head_sha=report.head_sha,
    )
    return dto.model_dump(mode="json")
