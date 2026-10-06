"""Immutable domain models for versioned analysis reports."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from changeguard.domain.findings import RiskFinding


class ReportStatus(StrEnum):
    """Overall completeness of an analysis report."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    INCOMPLETE = "incomplete"


class CoverageState(StrEnum):
    """Analysis support available for one rule target."""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class Evidence:
    """A repository location supporting an analysis finding."""

    path: str
    start_line: int | None = None
    end_line: int | None = None

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise ValueError("path cannot be empty or whitespace-only")
        if "\0" in self.path:
            raise ValueError("path cannot contain a null byte")
        if "\\" in self.path:
            raise ValueError("path must use POSIX separators")

        path = PurePosixPath(self.path)
        if path.is_absolute():
            raise ValueError("path must be relative")
        if ".." in path.parts:
            raise ValueError("path cannot contain '..'")
        if self.start_line is not None and self.start_line < 1:
            raise ValueError("start_line must be positive")
        if self.end_line is not None and self.end_line < 1:
            raise ValueError("end_line must be positive")
        if (
            self.start_line is not None
            and self.end_line is not None
            and self.end_line < self.start_line
        ):
            raise ValueError("end_line cannot be before start_line")


@dataclass(frozen=True, slots=True)
class Coverage:
    """Coverage result for one rule and target path or pattern."""

    rule_id: str
    target: str
    state: CoverageState
    reason: str

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("rule_id cannot be empty or whitespace-only")
        if not self.target.strip():
            raise ValueError("target cannot be empty or whitespace-only")
        if not self.reason.strip():
            raise ValueError("reason cannot be empty or whitespace-only")


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    """Immutable public analysis result before DTO serialization."""

    analysis_version: str
    repository: str
    pull_request: str
    base_sha: str | None
    head_sha: str | None
    status: ReportStatus
    findings: tuple[RiskFinding, ...]
    evidence: tuple[Evidence, ...]
    coverage: tuple[Coverage, ...]

    def __post_init__(self) -> None:
        if not self.analysis_version.strip():
            raise ValueError("analysis_version cannot be empty or whitespace-only")
        if not self.repository.strip():
            raise ValueError("repository cannot be empty or whitespace-only")
        if not self.pull_request.strip():
            raise ValueError("pull_request cannot be empty or whitespace-only")
        if self.status is ReportStatus.COMPLETE and not self.base_sha:
            raise ValueError("base_sha is required for a complete report")
        if self.status is ReportStatus.COMPLETE and not self.head_sha:
            raise ValueError("head_sha is required for a complete report")
