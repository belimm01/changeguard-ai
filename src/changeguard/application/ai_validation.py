import re

from pydantic import ValidationError

from changeguard.application.llm import MAX_RESPONSE_CHARS
from changeguard.domain.ai_output import Advisory, AiEnrichment, AiStatus, Citation
from changeguard.domain.corpus import source_lines
from changeguard.domain.retrieval import ContextPacket
from changeguard.dto.ai_output import AiOutputDto, CitationDto

_CONFIRMED = re.compile(
    r"\b(will break|is vulnerable|definitely|guaranteed|safe to merge|no risks?|no tests? (?:are )?needed)\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _citation_error(citation: CitationDto, context: ContextPacket) -> str | None:
    sources = {item.chunk.source_id: item.chunk for item in context.items}
    source = sources.get(citation.source_id)
    if source is None:
        return "unknown_source"
    if (citation.path, citation.side, citation.commit_sha, citation.blob_sha) != (
        source.path,
        source.side,
        source.commit_sha,
        source.blob_sha,
    ):
        return "provenance_mismatch"
    if (
        not source.start_line
        <= citation.start_line
        <= citation.end_line
        <= source.end_line
    ):
        return "range_mismatch"
    lines = source_lines(source.text)
    text = "".join(
        lines[
            citation.start_line - source.start_line : citation.end_line
            - source.start_line
            + 1
        ]
    )
    quote = _normalize(citation.quote)
    if not quote or quote not in _normalize(text):
        return "quote_mismatch"
    return None


def validate_ai_output(raw: str, context: ContextPacket) -> AiEnrichment:
    if len(raw) > MAX_RESPONSE_CHARS:
        return AiEnrichment(AiStatus.INVALID, rejected_reasons=("output_budget",))
    try:
        output = AiOutputDto.model_validate_json(raw)
    except (ValidationError, ValueError):
        return AiEnrichment(AiStatus.INVALID, rejected_reasons=("invalid_schema",))
    accepted: list[Advisory] = []
    rejected: list[str] = []
    for item in output.advisories:
        text = " ".join(
            (
                item.advisory_explanation,
                *item.recommended_tests,
                item.migration_considerations,
                item.rollback_considerations,
            )
        )
        if _CONFIRMED.search(text):
            rejected.append("unsupported_certainty")
            continue
        errors = [_citation_error(citation, context) for citation in item.citations]
        if any(errors):
            rejected.append(next(error for error in errors if error is not None))
            continue
        accepted.append(
            Advisory(
                item.advisory_explanation,
                item.advisory_severity,
                tuple(item.recommended_tests),
                item.migration_considerations,
                item.rollback_considerations,
                tuple(
                    Citation(
                        c.source_id,
                        c.path,
                        c.side,
                        c.commit_sha,
                        c.blob_sha,
                        c.start_line,
                        c.end_line,
                        c.quote,
                    )
                    for c in item.citations
                ),
            )
        )
    status = (
        AiStatus.PARTIAL
        if accepted and rejected
        else AiStatus.INVALID
        if rejected
        else AiStatus.AVAILABLE
    )
    return AiEnrichment(status, tuple(accepted), tuple(rejected))
