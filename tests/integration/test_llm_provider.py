import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from changeguard.adapters.llm_provider import OllamaAdapter
from changeguard.application.llm import LlmRequest
from changeguard.dto.ai_output import AiOutputDto


def request() -> LlmRequest:
    return LlmRequest(
        "local-test-model",
        "instructions",
        '{"sources": []}',
        AiOutputDto.model_json_schema(),
    )


def test_actual_structured_chat_mapping_and_usage() -> None:
    seen: list[dict[str, object]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        assert str(req.url) == "http://127.0.0.1:11434/api/chat"
        seen.append(json.loads(req.content))
        return httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": '{"advisories": []}'},
                "done": True,
                "prompt_eval_count": 20,
                "eval_count": 8,
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await OllamaAdapter(client).complete_structured(request())
            assert result.status == "available"
            assert (result.input_tokens, result.output_tokens) == (20, 8)

    asyncio.run(run())
    assert seen[0]["stream"] is False
    assert seen[0]["format"] == AiOutputDto.model_json_schema()
    assert "tools" not in seen[0]
    assert seen[0]["options"] == {"temperature": 0, "num_predict": 2048}


@pytest.mark.parametrize(
    "code,reason",
    [
        (429, "rate_limited"),
        (500, "provider_error"),
        (302, "provider_error"),
        (404, "provider_error"),
    ],
)
def test_safe_http_failures(code: int, reason: str) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(code, text="sensitive provider details")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await OllamaAdapter(client).complete_structured(request())
            assert result.reason == reason
            assert result.content is None

    asyncio.run(run())


@pytest.mark.parametrize(
    "body,reason",
    [
        (b"not json", "invalid_schema"),
        (
            json.dumps(
                {"message": {"role": "assistant", "content": "not json"}, "done": True}
            ).encode(),
            "invalid_schema",
        ),
        (
            json.dumps(
                {"message": {"role": "assistant", "content": ""}, "done": True}
            ).encode(),
            "empty_or_refused",
        ),
        (
            json.dumps(
                {
                    "message": {"role": "assistant", "content": '{"advisories": []}'},
                    "done": True,
                    "done_reason": "length",
                }
            ).encode(),
            "output_budget",
        ),
        (b"x" * 131073, "output_budget"),
    ],
)
def test_malformed_refusal_and_output_limits(body: bytes, reason: str) -> None:
    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, content=body))
        ) as client:
            result = await OllamaAdapter(client).complete_structured(request())
            assert result.reason == reason

    asyncio.run(run())


def test_timeout_and_budget_rejection() -> None:
    calls = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("sensitive details")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OllamaAdapter(client)
            assert (
                await adapter.complete_structured(
                    replace(request(), input_json="x" * 60001)
                )
            ).reason == "input_budget"
            assert (
                await adapter.complete_structured(
                    replace(request(), model="model:cloud")
                )
            ).reason == "local_model_required"
            assert (await adapter.complete_structured(request())).reason == "timeout"

    asyncio.run(run())
    assert calls == 1
