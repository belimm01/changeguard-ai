from dataclasses import dataclass
from enum import StrEnum

from changeguard.domain.content import Revision
from changeguard.domain.findings import RiskLevel


class AiStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    PARTIAL = "partial"
    INVALID = "invalid"
    NO_CONTEXT = "no_context"


@dataclass(frozen=True, slots=True)
class Citation:
    source_id: str
    path: str
    side: Revision
    commit_sha: str
    blob_sha: str
    start_line: int
    end_line: int
    quote: str


@dataclass(frozen=True, slots=True)
class Advisory:
    advisory_explanation: str
    advisory_severity: RiskLevel
    recommended_tests: tuple[str, ...]
    migration_considerations: str
    rollback_considerations: str
    citations: tuple[Citation, ...]


@dataclass(frozen=True, slots=True)
class AiEnrichment:
    status: AiStatus
    advisories: tuple[Advisory, ...] = ()
    rejected_reasons: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    omitted_chunks: int = 0
    reason: str = ""
    context_partial: bool = False

    @property
    def accepted_count(self) -> int:
        return len(self.advisories)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_reasons)
