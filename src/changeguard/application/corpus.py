from changeguard.domain.corpus import CorpusChunk, CorpusSource

MAX_CHUNK_BYTES = 8 * 1024
_MIN_CHUNK_BYTES = 4


def chunk_text(
    source: CorpusSource,
    max_bytes: int = MAX_CHUNK_BYTES,
) -> tuple[CorpusChunk, ...]:
    """Split source text into whole-line chunks of at most max_bytes UTF-8 bytes.

    A single line longer than the budget becomes its own chunk holding a
    UTF-8-safe prefix and marked truncated.
    """
    if max_bytes < _MIN_CHUNK_BYTES:
        raise ValueError(f"max_bytes must be at least {_MIN_CHUNK_BYTES}")

    chunks: list[CorpusChunk] = []
    buffer: list[str] = []
    buffer_bytes = 0
    start_line = 1

    for line_number, line in enumerate(_split_lines(source.text), start=1):
        line_bytes = len(line.encode("utf-8"))
        if buffer and buffer_bytes + line_bytes > max_bytes:
            chunks.append(
                CorpusChunk.from_source(
                    source, start_line, line_number - 1, "".join(buffer), False
                )
            )
            buffer, buffer_bytes = [], 0
        if line_bytes > max_bytes:
            prefix = _utf8_prefix(line, max_bytes)
            chunks.append(
                CorpusChunk.from_source(source, line_number, line_number, prefix, True)
            )
            continue
        if not buffer:
            start_line = line_number
        buffer.append(line)
        buffer_bytes += line_bytes

    if buffer:
        chunks.append(
            CorpusChunk.from_source(
                source, start_line, start_line + len(buffer) - 1, "".join(buffer), False
            )
        )
    return tuple(chunks)


def _split_lines(text: str) -> list[str]:
    """Split on LF only, keeping line endings, so numbers match Git line numbers."""
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def _utf8_prefix(text: str, max_bytes: int) -> str:
    return text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
