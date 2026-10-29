import pytest

from changeguard.application.corpus_paths import is_corpus_path


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "README",
        "services/api/README.rst",
        "docs/architecture.txt",
        "docs/adr/0001-storage.md",
        "adr/0002-queue.md",
        "api/openapi.yaml",
        "deploy/app.yml",
        "schemas/review.json",
        "schemas/review.avsc",
        "guides/SETUP.MD",
    ],
)
def test_is_corpus_path_includes_docs_adrs_and_schemas(path: str) -> None:
    assert is_corpus_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "src/changeguard/cli.py",
        "Dockerfile",
        "node_modules/pkg/README.md",
        "web/node_modules/pkg/package.json",
        ".venv/lib/site.json",
        "dist/openapi.yaml",
        "build/docs/index.md",
        ".git/config.json",
        "package-lock.json",
        "frontend/pnpm-lock.yaml",
        "uv.lock",
    ],
)
def test_is_corpus_path_excludes_code_vendored_generated_and_lockfiles(
    path: str,
) -> None:
    assert is_corpus_path(path) is False


def test_is_corpus_path_rejects_unsafe_path() -> None:
    with pytest.raises(ValueError):
        is_corpus_path("../docs/secret.md")
