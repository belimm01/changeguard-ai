from pathlib import Path

ROOT = Path(__file__).parents[2]
CONTRACT_DOCS = (
    ROOT / "README.md",
    ROOT / "docs/adr/0001-system-boundary.md",
    ROOT / "docs/threat-model.md",
)


def test_contract_docs_preserve_advisory_boundary() -> None:
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in CONTRACT_DOCS)

    assert "advisory" in text
    assert "may be wrong" in text
    for forbidden_claim in (
        "auto-merge",
        "auto-approve",
        "auto-block",
        "execute repository code",
    ):
        assert forbidden_claim in text


def test_contract_docs_name_untrusted_inputs_and_coverage() -> None:
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in CONTRACT_DOCS)

    for input_name in (
        "github api payloads",
        "file paths",
        "patches",
        "repository file content",
        "pr comments",
        "issue text",
        "future llm/tool output",
    ):
        assert input_name in text
    assert "partial" in text
    assert "unsupported" in text
    assert "never `safe`" in text


def test_threat_model_lists_required_mitigations() -> None:
    text = (ROOT / "docs/threat-model.md").read_text(encoding="utf-8").lower()

    for control in (
        "path",
        "symlink",
        "oversized",
        "credentials",
        "stale",
        "prompt injection",
        "pagination",
        "unsupported",
    ):
        assert control in text
