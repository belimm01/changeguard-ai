"""Provider-neutral boundary for structured LLM calls.

Application code depends only on LlmClient. The default client is disabled and
never touches the network; concrete providers live in adapters. Model output is
untrusted until citation validation accepts it.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class LlmStatus(StrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class LlmRequest:
    model: str
    prompt_name: str
    prompt_version: str
    prompt: str
    output_schema: Mapping[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 60.0
    max_output_tokens: int = 1024
    max_input_chars: int = 32_000

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("model cannot be empty or whitespace-only")
        if not self.prompt_name.strip() or not self.prompt_version.strip():
            raise ValueError("prompt name and version are required")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if self.max_input_chars < 1:
            raise ValueError("max_input_chars must be positive")


@dataclass(frozen=True, slots=True)
class LlmResult:
    status: LlmStatus
    content: str | None = None
    reason: str | None = None


class LlmClient(Protocol):
    async def complete_structured(self, request: LlmRequest) -> LlmResult: ...


class DisabledLlmClient:
    """Default client: AI is opt-in, so nothing is sent anywhere."""

    async def complete_structured(self, request: LlmRequest) -> LlmResult:
        return LlmResult(status=LlmStatus.UNAVAILABLE, reason="llm disabled")


async def complete_within_budget(client: LlmClient, request: LlmRequest) -> LlmResult:
    """Reject over-budget input before any provider sees it."""
    if len(request.prompt) > request.max_input_chars:
        return LlmResult(
            status=LlmStatus.REJECTED, reason="prompt exceeds input budget"
        )
    return await client.complete_structured(request)
