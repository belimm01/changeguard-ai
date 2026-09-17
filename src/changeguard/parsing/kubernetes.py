"""Safe, bounded multi-document YAML parsing for untrusted Kubernetes manifests."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

import yaml

DEFAULT_MAX_MANIFEST_BYTES = 1_000_000
DEFAULT_MAX_DOCUMENTS = 100


class ManifestProblem(StrEnum):
    OVERSIZED = "manifest exceeds the maximum analyzable size"
    MALFORMED = "manifest is not valid YAML"
    TOO_MANY_DOCUMENTS = "manifest has too many documents to analyze"
    TEMPLATE = "manifest contains unresolved template directives"


@dataclass(frozen=True, slots=True)
class ParsedManifests:
    documents: tuple[Mapping[str, object], ...] | None
    problem: ManifestProblem | None


def parse_kubernetes(
    text: str,
    *,
    max_bytes: int = DEFAULT_MAX_MANIFEST_BYTES,
    max_documents: int = DEFAULT_MAX_DOCUMENTS,
) -> ParsedManifests:
    if len(text.encode("utf-8")) > max_bytes:
        return ParsedManifests(None, ManifestProblem.OVERSIZED)
    if "{{" in text or "{%" in text:
        # Helm/Jinja templates are unrendered and cannot be safely analyzed here.
        return ParsedManifests(None, ManifestProblem.TEMPLATE)
    try:
        loaded = list(yaml.safe_load_all(text))
    except yaml.YAMLError:
        return ParsedManifests(None, ManifestProblem.MALFORMED)

    documents = tuple(doc for doc in loaded if isinstance(doc, Mapping))
    if len(documents) > max_documents:
        return ParsedManifests(None, ManifestProblem.TOO_MANY_DOCUMENTS)
    return ParsedManifests(documents, None)
