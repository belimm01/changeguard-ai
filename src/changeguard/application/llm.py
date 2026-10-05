import asyncio
import json
from dataclasses import dataclass
from typing import Protocol

MAX_INPUT_CHARS = 60_000
MAX_OUTPUT_TOKENS = 4096
MAX_RESPONSE_CHARS = 32_768


@dataclass(frozen=True, slots=True)
class LlmRequest:
    model: str
    instructions: str
    input_json: str
    output_schema: dict[str, object]
    prompt_version: str = "review-context-v1"
    timeout_seconds: float = 30.0
    max_output_tokens: int = 2048


@dataclass(frozen=True, slots=True)
class LlmResult:
    status: str
    content: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    reason: str = ""


class LlmAdapter(Protocol):
    async def complete_structured(self, request: LlmRequest) -> LlmResult: ...


class DisabledLlmAdapter:
    async def complete_structured(self, request: LlmRequest) -> LlmResult:
        return LlmResult("unavailable", reason="disabled")


def request_budget_error(request: LlmRequest) -> str | None:
    if (
        len(request.input_json)
        + len(request.instructions)
        + len(json.dumps(request.output_schema))
        > MAX_INPUT_CHARS
        or not 0 < request.max_output_tokens <= MAX_OUTPUT_TOKENS
        or not 0 < request.timeout_seconds <= 120
        or len(request.model) > 200
    ):
        return "input_budget"
    return None


async def complete_with_budget(adapter: LlmAdapter, request: LlmRequest) -> LlmResult:
    error = request_budget_error(request)
    if error:
        return LlmResult("unavailable", reason=error)
    try:
        async with asyncio.timeout(request.timeout_seconds):
            result = await adapter.complete_structured(request)
    except TimeoutError:
        return LlmResult("unavailable", reason="timeout")
    except Exception:  # noqa: BLE001 -- optional provider failures never replace deterministic results
        return LlmResult("unavailable", reason="provider_error")
    if result.content is not None and len(result.content) > MAX_RESPONSE_CHARS:
        return LlmResult("invalid", reason="output_budget")
    return result
