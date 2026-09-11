import argparse
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from pydantic import ValidationError

from changeguard.adapters.github import parse_github_changed_files
from changeguard.application.analysis import run_analysis
from changeguard.rules.python_dependencies import detect_python_dependency_changes
from changeguard.serialization import serialize_findings


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    argparse.ArgumentParser().parse_args(argv)

    if stdin is None:
        stdin = sys.stdin

    if stdout is None:
        stdout = sys.stdout

    if stderr is None:
        stderr = sys.stderr

    try:
        payload = json.load(stdin)
    except (
        json.JSONDecodeError,
        UnicodeError,
        OSError,
    ):
        print("invalid input", file=stderr)
        return 2

    try:
        change_set = parse_github_changed_files(payload)
    except ValidationError:
        print("invalid input", file=stderr)
        return 2

    findings = run_analysis(
        change_set,
        rules=(detect_python_dependency_changes,),
    )
    result = serialize_findings(findings)
    json.dump(result, stdout)
    stdout.write("\n")
    return 0
