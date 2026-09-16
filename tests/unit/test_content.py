import pytest

from changeguard.domain.content import (
    DiffLineEvidence,
    FileContent,
    FileContentRef,
    Revision,
)


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


def test_diff_line_evidence_accepts_valid_props() -> None:
    diff = DiffLineEvidence(
        path="src/changeguard/models.py",
        side=Revision.HEAD,
        start_line=1,
        end_line=2,
        sha="sha",
    )

    assert diff.path == "src/changeguard/models.py"
    assert diff.start_line == 1
    assert diff.end_line == 2
    assert diff.side == Revision.HEAD
    assert diff.sha == "sha"


def test_diff_line_evidence_rejects_invalid_path() -> None:
    with pytest.raises(ValueError, match="path cannot contain '..'"):
        DiffLineEvidence(
            path="../secrets",
            side=Revision.BASE,
            start_line=1,
            end_line=2,
            sha="sha",
        )


def test_diff_line_evidence_rejects_non_positive_lines() -> None:
    with pytest.raises(ValueError, match="start_line must be greater than 0"):
        DiffLineEvidence(
            path="src/changeguard/models.py",
            side=Revision.BASE,
            start_line=0,
            end_line=1,
            sha="sha",
        )
    with pytest.raises(ValueError, match="end_line must be greater than 0"):
        DiffLineEvidence(
            path="src/changeguard/models.py",
            side=Revision.BASE,
            start_line=1,
            end_line=0,
            sha="sha",
        )


def test_diff_line_evidence_rejects_end_before_start() -> None:
    with pytest.raises(ValueError, match="less than or equal to end_line"):
        DiffLineEvidence(
            path="src/changeguard/models.py",
            side=Revision.BASE,
            start_line=5,
            end_line=2,
            sha="sha",
        )


def test_diff_line_evidence_rejects_empty_sha() -> None:
    with pytest.raises(ValueError, match="sha cannot be empty"):
        DiffLineEvidence(
            path="src/changeguard/models.py",
            side=Revision.BASE,
            start_line=1,
            end_line=2,
            sha="",
        )


def test_diff_line_evidence_content_mapping() -> None:
    diff = DiffLineEvidence.from_content(
        content=FileContent(
            revision=Revision.BASE,
            sha="sha",
            text="line 1\nline 2",
            size=12,
        ),
        path="src/changeguard/models.py",
        start_line=1,
        end_line=2,
    )
    assert diff.path == "src/changeguard/models.py"
    assert diff.start_line == 1
    assert diff.end_line == 2
    assert diff.side == Revision.BASE
    assert diff.sha == "sha"


def test_diff_line_evidence_from_content_validates() -> None:
    with pytest.raises(ValueError, match="less than or equal to end_line"):
        DiffLineEvidence.from_content(
            content=FileContent(revision=Revision.HEAD, sha="abc", text="x", size=1023),
            path="a.py",
            start_line=5,
            end_line=2,
        )
