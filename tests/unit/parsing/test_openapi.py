import textwrap

from changeguard.parsing.openapi import SpecProblem, parse_openapi


def _spec(body: str) -> str:
    return textwrap.dedent(body).lstrip()


def test_parses_valid_openapi_3() -> None:
    spec = parse_openapi(
        _spec("""
            openapi: 3.1.0
            info: {title: Demo, version: "1.0"}
            paths: {}
        """)
    )
    assert spec.problem is None
    assert spec.document is not None
    assert str(spec.document["openapi"]).startswith("3.")


def test_rejects_swagger_2() -> None:
    spec = parse_openapi(
        _spec("""
            swagger: "2.0"
            info: {title: Demo, version: "1.0"}
            paths: {}
        """)
    )
    assert spec.document is None
    assert spec.problem is SpecProblem.SWAGGER_2


def test_rejects_mapping_without_version_key() -> None:
    spec = parse_openapi(
        _spec("""
            info: {title: Demo, version: "1.0"}
            paths: {}
        """)
    )
    assert spec.document is None
    assert spec.problem is SpecProblem.UNSUPPORTED_VERSION


def test_rejects_non_string_version() -> None:
    spec = parse_openapi(
        _spec("""
            openapi: [3, 1, 0]
            paths: {}
        """)
    )
    assert spec.document is None
    assert spec.problem is SpecProblem.UNSUPPORTED_VERSION


def test_rejects_non_mapping_root() -> None:
    spec = parse_openapi(
        _spec("""
            - a
            - b
        """)
    )
    assert spec.document is None
    assert spec.problem is SpecProblem.NOT_A_MAPPING


def test_rejects_empty_document() -> None:
    spec = parse_openapi("")
    assert spec.document is None
    assert spec.problem is SpecProblem.NOT_A_MAPPING


def test_rejects_malformed_yaml() -> None:
    spec = parse_openapi("key: [unclosed")
    assert spec.document is None
    assert spec.problem is SpecProblem.MALFORMED


def test_oversized_checked_before_parsing() -> None:
    # Malformed AND oversized: the size guard must run before yaml.safe_load,
    # so we should never spend parsing effort on oversized untrusted input.
    spec = parse_openapi("key: [unclosed and too large", max_bytes=5)
    assert spec.document is None
    assert spec.problem is SpecProblem.OVERSIZED
