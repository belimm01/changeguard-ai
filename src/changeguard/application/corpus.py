from dataclasses import replace
from pathlib import PurePosixPath

from changeguard.domain.content import FileContent, RemoteContentResult
from changeguard.domain.corpus import (
    Corpus,
    CorpusChunk,
    CorpusDiagnostic,
    source_lines,
)
from changeguard.domain.models import validate_relative_path
from changeguard.domain.reports import CoverageState


def split_chunk(chunk: CorpusChunk, max_lines: int) -> tuple[CorpusChunk, ...]:
    if max_lines <= 0:
        raise ValueError("max_lines must be positive")
    lines = source_lines(chunk.text)
    if not lines:
        return ()
    if len(lines) != chunk.end_line - chunk.start_line + 1:
        raise ValueError("line range must match text line count")
    if len(lines) <= max_lines:
        return (chunk,)
    return tuple(
        replace(
            chunk,
            start_line=chunk.start_line + offset,
            end_line=chunk.start_line + min(offset + max_lines, len(lines)) - 1,
            text="".join(lines[offset : offset + max_lines]),
        )
        for offset in range(0, len(lines), max_lines)
    )


def is_corpus_path(path: str) -> bool:
    source = PurePosixPath(path)
    if any(
        part in {".git", "node_modules", ".venv", "dist", "build"}
        for part in source.parts[:-1]
    ):
        return False
    if source.suffix == ".lock" or source.name in {
        "package-lock.json",
        "npm-shrinkwrap.json",
        "pnpm-lock.yaml",
    }:
        return False
    return (
        source.name.startswith("README")
        or (len(source.parts) > 1 and source.parts[0] in {"docs", "adr"})
        or source.suffix in {".md", ".rst", ".yaml", ".yml", ".json", ".avsc"}
    )


MAX_FILES = 32
MAX_CHUNKS = 128
MAX_CHUNK_BYTES = 8 * 1024
MAX_CORPUS_BYTES = 256 * 1024


def truncate_utf8(text: str, max_bytes: int) -> tuple[str, bool]:
    if max_bytes < 0:
        raise ValueError("max_bytes must be nonnegative")
    encoded = text.encode("utf-8")
    return encoded[:max_bytes].decode("utf-8", errors="ignore"), len(
        encoded
    ) > max_bytes


def extract_corpus(contents: tuple[FileContent | RemoteContentResult, ...]) -> Corpus:
    chunks: list[CorpusChunk] = []
    diagnostics: list[CorpusDiagnostic] = []
    files: list[FileContent] = []
    for entry in contents:
        if isinstance(entry, RemoteContentResult):
            files.extend((entry.content,) if entry.content is not None else ())
            for coverage in entry.coverage:
                if coverage.state is not CoverageState.SUPPORTED:
                    diagnostics.append(
                        CorpusDiagnostic(
                            coverage.target,
                            entry.content.revision if entry.content else None,
                            "upstream_content_unavailable",
                        )
                    )
        else:
            files.append(entry)
    excluded = omitted = selected = used = 0
    seen: set[tuple[str, str, str, str]] = set()
    original_text: dict[tuple[str, str, str, str], str] = {}
    conflicting: set[tuple[str, str, str, str]] = set()
    for candidate in files:
        key = (
            candidate.path or "",
            candidate.revision,
            candidate.sha,
            candidate.blob_sha or "",
        )
        if key in original_text and original_text[key] != candidate.text:
            conflicting.add(key)
        original_text[key] = candidate.text
    ordered = sorted(
        files, key=lambda c: (c.path or "", c.revision, c.sha, c.blob_sha or "")
    )
    for content in ordered:
        path = content.path or ""
        try:
            validate_relative_path(path)
        except ValueError:
            diagnostics.append(
                CorpusDiagnostic("<invalid>", content.revision, "invalid_path")
            )
            continue
        if not is_corpus_path(path):
            excluded += 1
            continue
        if (
            not content.sha.strip()
            or not content.blob_sha
            or not content.blob_sha.strip()
        ):
            diagnostics.append(
                CorpusDiagnostic(path, content.revision, "missing_provenance")
            )
            continue
        identity = (path, content.revision, content.sha, content.blob_sha)
        if identity in seen:
            continue
        seen.add(identity)
        if identity in conflicting:
            diagnostics.append(
                CorpusDiagnostic(path, content.revision, "conflicting_source")
            )
            continue
        if (
            selected >= MAX_FILES
            or len(chunks) >= MAX_CHUNKS
            or used >= MAX_CORPUS_BYTES
        ):
            omitted += 1
            continue
        selected += 1
        try:
            text, truncated = truncate_utf8(content.text, MAX_CORPUS_BYTES - used)
        except UnicodeEncodeError:
            diagnostics.append(CorpusDiagnostic(path, content.revision, "invalid_utf8"))
            continue
        if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
            diagnostics.append(
                CorpusDiagnostic(path, content.revision, "binary_content")
            )
            continue
        file_chunks: list[CorpusChunk] = []
        pending = ""
        first = 1
        last = 0
        suffix = PurePosixPath(path).suffix
        kind = {
            ".md": "text/markdown",
            ".json": "application/json",
            ".avsc": "application/avro",
            ".yaml": "application/yaml",
            ".yml": "application/yaml",
        }.get(suffix, "text/plain")

        for line_number, line in enumerate(source_lines(text), 1):
            if len((pending + line).encode("utf-8")) > MAX_CHUNK_BYTES:
                if pending:
                    file_chunks.append(
                        CorpusChunk(
                            path,
                            content.revision,
                            content.sha,
                            content.blob_sha,
                            pending,
                            first,
                            last,
                            kind,
                            False,
                        )
                    )
                pending = ""
                first = line_number
                if len(chunks) + len(file_chunks) >= MAX_CHUNKS:
                    truncated = True
                    break
            prefix, long_line = truncate_utf8(line, MAX_CHUNK_BYTES)
            pending += prefix
            last = line_number
            if long_line:
                truncated = True
                break
        if pending:
            file_chunks.append(
                CorpusChunk(
                    path,
                    content.revision,
                    content.sha,
                    content.blob_sha,
                    pending,
                    first,
                    last,
                    kind,
                    False,
                )
            )
        if truncated:
            diagnostics.append(
                CorpusDiagnostic(path, content.revision, "text_truncated")
            )
        for chunk in file_chunks:
            chunks.append(replace(chunk, truncated=truncated))
            used += len(chunk.text.encode("utf-8"))
    diagnostics.sort(
        key=lambda diagnostic: (
            diagnostic.path,
            diagnostic.side or "",
            diagnostic.reason,
        )
    )
    return Corpus(tuple(chunks), tuple(diagnostics), excluded, omitted)
