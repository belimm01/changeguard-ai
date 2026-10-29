from pathlib import PurePosixPath

from changeguard.domain.models import validate_relative_path

_DOC_ROOTS = frozenset({"docs", "adr"})
_SUFFIXES = frozenset({".md", ".rst", ".yaml", ".yml", ".json", ".avsc"})
_EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", "dist", "build"})
_LOCKFILES = frozenset(
    {
        "Cargo.lock",
        "Gemfile.lock",
        "composer.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "yarn.lock",
    }
)


def is_corpus_path(path: str) -> bool:
    """Return True when a repository path is documentation, an ADR or a schema."""
    validate_relative_path(path)
    parts = PurePosixPath(path).parts
    *directories, name = parts
    if any(directory in _EXCLUDED_DIRS for directory in directories):
        return False
    if name in _LOCKFILES:
        return False
    if name.startswith("README"):
        return True
    if directories and directories[0] in _DOC_ROOTS:
        return True
    return PurePosixPath(name).suffix.lower() in _SUFFIXES
