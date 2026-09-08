import pytest

from changeguard.adapters.github import parse_github_changed_files
from changeguard.application.analysis import run_analysis
from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.models import ChangeSet
from changeguard.rules.python_dependencies import detect_python_dependency_changes


def test_returns_no_findings_when_no_rules_are_configured() -> None:
    assert run_analysis(ChangeSet(files=()), rules=()) == ()


def test_runs_the_python_dependency_rule() -> None:
    payload = [
        {
            "filename": "pyproject.toml",
            "status": "modified",
            "additions": 1,
            "deletions": 0,
            "patch": "@@ -1 +1 @@",
        },
        {
            "filename": "README.md",
            "status": "deleted",
            "additions": 0,
            "deletions": 8,
            "patch": None,
        },
    ]

    change_set = parse_github_changed_files(payload)

    assert run_analysis(
        change_set,
        rules=(detect_python_dependency_changes,),
    ) == (
        RiskFinding(
            rule_id="python-dependency-change",
            level=RiskLevel.MEDIUM,
            summary=(
                "Python dependency files changed; "
                "review dependency and lockfile consistency."
            ),
            evidence_paths=("pyproject.toml",),
        ),
    )


def test_flattens_findings_in_rule_order() -> None:
    first = RiskFinding(
        rule_id="first-rule",
        level=RiskLevel.LOW,
        summary="First finding",
        evidence_paths=("first.txt",),
    )
    first_follow_up = RiskFinding(
        rule_id="first-rule",
        level=RiskLevel.MEDIUM,
        summary="First follow-up finding",
        evidence_paths=("first-follow-up.txt",),
    )
    second = RiskFinding(
        rule_id="second-rule",
        level=RiskLevel.HIGH,
        summary="Second finding",
        evidence_paths=("second.txt",),
    )

    def first_rule(change_set: ChangeSet) -> tuple[RiskFinding, ...]:
        return (first, first_follow_up)

    def second_rule(change_set: ChangeSet) -> tuple[RiskFinding, ...]:
        return (second,)

    assert run_analysis(
        ChangeSet(files=()),
        rules=(first_rule, second_rule),
    ) == (first, first_follow_up, second)


def test_calls_each_rule_once() -> None:
    change_set = ChangeSet(files=())
    calls: list[tuple[str, ChangeSet]] = []

    def first_rule(received_change_set: ChangeSet) -> tuple[RiskFinding, ...]:
        calls.append(("first", received_change_set))
        return ()

    def second_rule(received_change_set: ChangeSet) -> tuple[RiskFinding, ...]:
        calls.append(("second", received_change_set))
        return ()

    assert run_analysis(change_set, rules=(first_rule, second_rule)) == ()
    assert calls == [("first", change_set), ("second", change_set)]
    assert all(received_change_set is change_set for _, received_change_set in calls)


def test_ignores_empty_results_from_configured_rules() -> None:
    finding = RiskFinding(
        rule_id="non-empty-rule",
        level=RiskLevel.MEDIUM,
        summary="A finding",
        evidence_paths=("example.txt",),
    )

    def empty_rule(change_set: ChangeSet) -> tuple[RiskFinding, ...]:
        return ()

    def non_empty_rule(change_set: ChangeSet) -> tuple[RiskFinding, ...]:
        return (finding,)

    result = run_analysis(
        ChangeSet(files=()),
        rules=(empty_rule, non_empty_rule),
    )

    assert result == (finding,)
    assert isinstance(result, tuple)


def test_propagates_a_rule_exception_and_stops() -> None:
    calls: list[str] = []

    def failing_rule(change_set: ChangeSet) -> tuple[RiskFinding, ...]:
        calls.append("failing")
        raise RuntimeError("rule failed")

    def later_rule(change_set: ChangeSet) -> tuple[RiskFinding, ...]:
        calls.append("later")
        return ()

    with pytest.raises(RuntimeError, match="rule failed"):
        run_analysis(
            ChangeSet(files=()),
            rules=(failing_rule, later_rule),
        )

    assert calls == ["failing"]
