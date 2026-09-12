import io

from changeguard.cli import main


def test_empty_payload_returns_empty_json_array() -> None:
    stdin = io.StringIO("[]")
    sink = io.StringIO()
    rc = main(argv=[], stdin=stdin, stdout=sink)
    assert rc == 0
    assert sink.getvalue() == "[]\n"
