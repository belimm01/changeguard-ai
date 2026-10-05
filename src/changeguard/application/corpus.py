from dataclasses import replace
from pathlib import PurePosixPath

from changeguard.domain.corpus import CorpusChunk


def split_chunk(chunk: CorpusChunk, max_lines: int) -> tuple[CorpusChunk, ...]:
    if max_lines <= 0:
        raise ValueError("max_lines must be positive")
    lines = chunk.text.splitlines(keepends=True)
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
