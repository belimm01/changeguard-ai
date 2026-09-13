import subprocess
import sys


def test_subprocess_empty_payload() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "changeguard"],
        input="[]",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == "[]\n"
    assert result.stderr == ""


def test_subprocess_invalid_json_has_no_traceback() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "changeguard"],
        input="invalid json",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == "invalid input\n"


def test_subprocess_help_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "changeguard", "--help"],
        input="[]",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "-h, --help" in result.stdout
    assert result.stderr == ""


def test_subprocess_unknown_argument_exits_two() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "changeguard", "--unknown-argument"],
        input="[]",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "unrecognized arguments" in result.stderr
