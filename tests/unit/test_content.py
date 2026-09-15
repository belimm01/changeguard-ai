import pytest

from changeguard.domain.content import FileContentRef, Revision


def test_content_invalid_path_raises_value_error() -> None:
    invalid_paths = ["", "../secrets", "/etc/passwd", "a\\b", "a\0b"]
    for invalid_path in invalid_paths:
        with pytest.raises(ValueError):
            FileContentRef(
                owner="owner",
                name="name",
                path=invalid_path,
                revision=Revision.BASE,
                sha="sha",
            )


def test_content_accept_valid_path() -> None:
    content = FileContentRef(
        owner="owner",
        name="name",
        path="src/changeguard/models.py",
        revision=Revision.BASE,
        sha="sha",
    )
    assert content.path == "src/changeguard/models.py"
