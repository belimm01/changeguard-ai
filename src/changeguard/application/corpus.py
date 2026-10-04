from dataclasses import replace

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
