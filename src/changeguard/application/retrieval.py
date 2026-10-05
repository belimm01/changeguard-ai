import re
from pathlib import PurePosixPath

from changeguard.domain.corpus import Corpus, CorpusChunk
from changeguard.domain.findings import RiskFinding
from changeguard.domain.retrieval import ContextItem, ContextPacket

MAX_CONTEXT_CHUNKS = 12
MAX_CHUNKS_PER_FILE = 4
MAX_CONTEXT_BYTES = 24 * 1024
_STOP_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "in",
        "is",
        "for",
        "on",
        "how",
        "what",
        "with",
    }
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\w]+", text.casefold())) - _STOP_WORDS


def _score(chunk: CorpusChunk, path: str, query: str) -> tuple[int, tuple[str, ...]]:
    tokens = _tokens(path + " " + query)
    if not tokens:
        return 0, ()
    overlap = tokens & _tokens(chunk.text)
    headings = " ".join(
        line.lstrip("# ") for line in chunk.text.splitlines() if line.startswith("#")
    )
    score = len(overlap) + 2 * len(tokens & _tokens(headings))
    reasons: list[str] = ["text_overlap"] if overlap else []
    if path:
        source = PurePosixPath(chunk.path)
        changed = PurePosixPath(path)
        if source.name == changed.name:
            score += 10
            reasons.append("filename_match")
        if set(source.parts[:-1]) & set(changed.parts[:-1]):
            score += 4
            reasons.append("directory_match")
        if changed.stem.casefold() in _tokens(chunk.path):
            score += 6
            reasons.append("path_token_match")
        if (
            changed.suffix in {".yaml", ".yml", ".json", ".avsc"}
            and source.suffix == changed.suffix
        ):
            score += 2
            reasons.append("schema_kind_match")
    return score, tuple(reasons)


def retrieve_context(
    corpus: Corpus,
    changed_paths: tuple[str, ...] = (),
    findings: tuple[RiskFinding, ...] = (),
    *,
    question: str = "",
) -> ContextPacket:
    if len(question) > 4000:
        raise ValueError("question exceeds character budget")
    paths = tuple(
        sorted(
            set(changed_paths)
            | {p for finding in findings for p in finding.evidence_paths}
        )
    )
    candidates: list[ContextItem] = []
    unique = {chunk.source_id: chunk for chunk in corpus.chunks}
    for chunk in unique.values():
        scores: list[int] = []
        reasons: set[str] = set()
        matched: list[str] = []
        for path in paths or ("",):
            query = (
                question
                + " "
                + " ".join(
                    finding.rule_id + " " + finding.summary
                    for finding in findings
                    if path in finding.evidence_paths
                )
            )
            score, why = _score(chunk, path, query)
            if score:
                scores.append(score)
                reasons.update(why)
                if path:
                    matched.append(path)
        if scores:
            candidates.append(
                ContextItem(chunk, max(scores), tuple(sorted(reasons)), tuple(matched))
            )
    candidates.sort(
        key=lambda item: (
            -item.score,
            item.chunk.path,
            item.chunk.side,
            item.chunk.start_line,
            item.chunk.commit_sha,
            item.chunk.blob_sha,
            item.chunk.source_id,
        )
    )
    selected: list[ContextItem] = []
    counts: dict[str, int] = {}
    used = 0
    for item in candidates:
        size = len(item.chunk.text.encode("utf-8"))
        if len(selected) >= MAX_CONTEXT_CHUNKS or used + size > MAX_CONTEXT_BYTES:
            continue
        if any(
            counts.get(path, 0) >= MAX_CHUNKS_PER_FILE for path in item.matched_paths
        ):
            continue
        selected.append(item)
        used += size
        for path in item.matched_paths:
            counts[path] = counts.get(path, 0) + 1
    return ContextPacket(
        tuple(selected),
        len(candidates) - len(selected),
        len(unique) - len(candidates),
        corpus.partial,
    )
