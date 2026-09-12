import io
import json

import pytest

from changeguard.cli import main


def test_empty_payload_returns_empty_json_array() -> None:
    stdin = io.StringIO("[]")
    sink = io.StringIO()
    rc = main(argv=[], stdin=stdin, stdout=sink)
    assert rc == 0
    assert sink.getvalue() == "[]\n"


def test_malformed_json_returns_error_code() -> None:
    stdin = io.StringIO("invalid json")
    sink = io.StringIO()
    stderr = io.StringIO()
    rc = main(argv=[], stdin=stdin, stdout=sink, stderr=stderr)
    assert rc == 2
    assert sink.getvalue() == ""
    assert stderr.getvalue() == "invalid input\n"


def test_pyproject_change_produces_dependency_finding() -> None:
    payload = [
        {
            "filename": "pyproject.toml",
            "status": "modified",
            "additions": 3,
            "deletions": 2,
            "patch": None,
        }
    ]
    sink = io.StringIO()
    rc = main(argv=[], stdin=io.StringIO(json.dumps(payload)), stdout=sink)
    findings = json.loads(sink.getvalue())
    assert rc == 0
    assert findings[0]["evidence_paths"] == ["pyproject.toml"]
    assert findings[0]["level"] == "medium"
    assert (
        findings[0]["summary"]
        == "Python dependency files changed; review dependency and lockfile consistency."
    )
    assert findings[0]["rule_id"] == "python-dependency-change"


def test_help_exits_zero() -> None:
    stdin = io.StringIO("")
    sink = io.StringIO()
    stderr = io.StringIO()
    with pytest.raises(SystemExit) as exc:
        main(argv=["--help"], stdin=stdin, stdout=sink, stderr=stderr)
    assert exc.value.code == 0


def test_invalid_payload_never_echoes_secret() -> None:
    sink = io.StringIO()
    stderr = io.StringIO()
    SECRET = "SUPER-SECRET-TOKEN-123"
    payload = [
        {
            "filename": "app.py",
            "status": "modified",
            "additions": SECRET,
            "deletions": 0,
            "patch": None,
        }
    ]
    stdin = io.StringIO(json.dumps(payload))
    rc = main(argv=[], stdin=stdin, stdout=sink, stderr=stderr)
    assert rc == 2
    assert sink.getvalue() == ""
    assert SECRET not in stderr.getvalue()
