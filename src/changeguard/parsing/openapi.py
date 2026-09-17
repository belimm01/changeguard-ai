from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

import yaml

DEFAULT_MAX_SPEC_BYTES = 1_000_000


class SpecProblem(StrEnum):
    OVERSIZED = "spec exceeds the maximum analyzable size"
    MALFORMED = "spec is not valid YAML or JSON"
    NOT_A_MAPPING = "spec root is not a mapping"
    SWAGGER_2 = "OpenAPI 2.0 (swagger) is not supported"
    UNSUPPORTED_VERSION = "only OpenAPI 3.x is supported"


@dataclass(frozen=True, slots=True)
class ParsedSpec:
    document: Mapping[str, object] | None
    problem: SpecProblem | None  # None => usable for analysis


def parse_openapi(text: str, *, max_bytes: int = DEFAULT_MAX_SPEC_BYTES) -> ParsedSpec:
    parsed_result = None
    if len(text.encode("utf-8")) > max_bytes:
        return ParsedSpec(None, SpecProblem.OVERSIZED)

    try:
        parsed_result = yaml.safe_load(text)
    except yaml.YAMLError:
        return ParsedSpec(None, SpecProblem.MALFORMED)

    if not isinstance(parsed_result, Mapping):
        return ParsedSpec(None, SpecProblem.NOT_A_MAPPING)
    if "swagger" in parsed_result:
        return ParsedSpec(None, SpecProblem.SWAGGER_2)
    version = parsed_result.get("openapi")
    if not isinstance(version, str) or not version.startswith("3."):
        return ParsedSpec(None, SpecProblem.UNSUPPORTED_VERSION)
    return ParsedSpec(parsed_result, None)
