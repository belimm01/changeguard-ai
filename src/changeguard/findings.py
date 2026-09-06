"""Evidence-backed advisory findings produced by ChangeGuard rules."""

from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    """Advisory importance of a finding."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class RiskFinding:
    """A deterministic finding with repository paths as evidence."""

    rule_id: str
    level: RiskLevel
    summary: str
    evidence_paths: tuple[str, ...]
