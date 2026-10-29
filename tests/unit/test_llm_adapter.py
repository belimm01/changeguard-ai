import asyncio

import pytest

from changeguard.application.llm import (
    DisabledLlmClient,
    LlmRequest,
    LlmResult,
    LlmStatus,
    complete_within_budget,
)


def request(prompt: str = "question", max_input_chars: int = 100) -> LlmRequest:
    return LlmRequest(
        model="test-model",
        prompt_name="advisory",
        prompt_version="1",
        prompt=prompt,
        max_input_chars=max_input_chars,
    )


class RecordingClient:
    def __init__(self) -> None:
        self.requests: list[LlmRequest] = []

    async def complete_structured(self, request: LlmRequest) -> LlmResult:
        self.requests.append(request)
        return LlmResult(status=LlmStatus.OK, content="{}")


def test_disabled_adapter_returns_unavailable_without_network() -> None:
    result = asyncio.run(DisabledLlmClient().complete_structured(request()))

    assert result.status is LlmStatus.UNAVAILABLE


def test_over_budget_prompt_is_rejected_before_client_is_called() -> None:
    client = RecordingClient()

    result = asyncio.run(complete_within_budget(client, request("x" * 11, 10)))

    assert result.status is LlmStatus.REJECTED
    assert client.requests == []


def test_prompt_within_budget_reaches_client() -> None:
    client = RecordingClient()

    result = asyncio.run(complete_within_budget(client, request("x" * 10, 10)))

    assert result.status is LlmStatus.OK
    assert len(client.requests) == 1


@pytest.mark.parametrize(
    "override",
    [
        {"model": " "},
        {"prompt_name": ""},
        {"timeout_seconds": 0},
        {"max_output_tokens": 0},
        {"max_input_chars": 0},
    ],
)
def test_request_rejects_invalid_settings(override: dict[str, object]) -> None:
    fields: dict[str, object] = {
        "model": "m",
        "prompt_name": "p",
        "prompt_version": "1",
        "prompt": "q",
    }
    with pytest.raises(ValueError):
        LlmRequest(**(fields | override))  # type: ignore[arg-type]
