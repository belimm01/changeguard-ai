"""Safe JSON parsing for untrusted Avro schema inputs."""

import json
from dataclasses import dataclass
from enum import StrEnum

DEFAULT_MAX_SCHEMA_BYTES = 1_000_000


class AvroProblem(StrEnum):
    OVERSIZED = "schema exceeds the maximum analyzable size"
    MALFORMED = "schema is not valid JSON"


@dataclass(frozen=True, slots=True)
class ParsedAvro:
    schema: object | None
    problem: AvroProblem | None  # None => JSON parsed (still may be unsupported shape)


def parse_avro(text: str, *, max_bytes: int = DEFAULT_MAX_SCHEMA_BYTES) -> ParsedAvro:
    if len(text.encode("utf-8")) > max_bytes:
        return ParsedAvro(None, AvroProblem.OVERSIZED)
    try:
        schema = json.loads(text)
    except json.JSONDecodeError:
        return ParsedAvro(None, AvroProblem.MALFORMED)
    return ParsedAvro(schema, None)
