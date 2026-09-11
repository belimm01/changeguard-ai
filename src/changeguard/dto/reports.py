"""Pydantic DTOs for versioned analysis reports."""

from pydantic import BaseModel, ConfigDict

from changeguard.dto.findings import FindingDto


class EvidenceDto(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    start_line: int | None = None
    end_line: int | None = None


class CoverageDto(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    target: str
    state: str
    reason: str


class AnalysisReportDto(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str
    analysis_version: str
    repository: str
    pull_request: str
    base_sha: str | None
    head_sha: str | None
    status: str
    findings: list[FindingDto]
    evidence: list[EvidenceDto]
    coverage: list[CoverageDto]
