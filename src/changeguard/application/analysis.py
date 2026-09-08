"""Application-level orchestration for deterministic analysis rules."""

from collections.abc import Callable

from changeguard.domain.findings import RiskFinding
from changeguard.domain.models import ChangeSet

# A rule is any function with this input/output contract. This keeps rules
# independently testable and avoids introducing a framework container.
AnalysisRule = Callable[[ChangeSet], tuple[RiskFinding, ...]]


def run_analysis(
    change_set: ChangeSet,
    rules: tuple[AnalysisRule, ...],
) -> tuple[RiskFinding, ...]:
    return tuple(finding for rule in rules for finding in rule(change_set))
