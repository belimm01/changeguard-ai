import asyncio
from dataclasses import replace

from changeguard.application.llm import (
    DisabledLlmAdapter,
    LlmRequest,
    LlmResult,
    complete_with_budget,
)


def request() -> LlmRequest:
    return LlmRequest("fake", "instructions", "{}", {})


def test_disabled_adapter_returns_unavailable_without_network() -> None:
    result = asyncio.run(complete_with_budget(DisabledLlmAdapter(), request()))
    assert result.reason == "disabled"


def test_budget_prevents_call() -> None:
    class NeverCalled:
        async def complete_structured(self, request: LlmRequest) -> LlmResult:
            raise AssertionError("must not call")

    assert (
        asyncio.run(
            complete_with_budget(
                NeverCalled(), replace(request(), input_json="x" * 60001)
            )
        ).reason
        == "input_budget"
    )


def test_timeout_and_cancellation() -> None:
    class Slow:
        async def complete_structured(self, request: LlmRequest) -> LlmResult:
            await asyncio.sleep(10)
            return LlmResult("available", "{}")

    assert (
        asyncio.run(
            complete_with_budget(Slow(), replace(request(), timeout_seconds=0.001))
        ).reason
        == "timeout"
    )

    async def cancel() -> None:
        task = asyncio.create_task(complete_with_budget(Slow(), request()))
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return
        raise AssertionError("cancellation must propagate")

    asyncio.run(cancel())
