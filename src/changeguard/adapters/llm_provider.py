"""Opt-in Ollama structured chat adapter; the caller owns the HTTP client."""

import json
from typing import Annotated

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from changeguard.application.llm import LlmRequest, LlmResult, request_budget_error
from changeguard.dto.ai_output import AiOutputDto

MAX_HTTP_RESPONSE_BYTES = 131_072


class _Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: str
    content: Annotated[str, Field(max_length=32_768)]
    tool_calls: list[object] = Field(default_factory=list)


class _Response(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message: _Message
    done: bool
    done_reason: str = "stop"
    prompt_eval_count: Annotated[int, Field(ge=0, strict=True)] = 0
    eval_count: Annotated[int, Field(ge=0, strict=True)] = 0


class OllamaAdapter:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def complete_structured(self, request: LlmRequest) -> LlmResult:
        error = request_budget_error(request)
        if error:
            return LlmResult("unavailable", reason=error)
        if (
            not request.model.strip()
            or request.model == "disabled"
            or "cloud" in request.model.casefold()
        ):
            return LlmResult("unavailable", reason="local_model_required")
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.instructions},
                {"role": "user", "content": request.input_json},
            ],
            "format": request.output_schema,
            "stream": False,
            "think": False,
            "keep_alive": 0,
            "options": {"temperature": 0, "num_predict": request.max_output_tokens},
        }
        try:
            async with self._client.stream(
                "POST",
                "http://127.0.0.1:11434/api/chat",
                json=payload,
                timeout=request.timeout_seconds,
                follow_redirects=False,
            ) as response:
                if response.status_code == 429:
                    return LlmResult("unavailable", reason="rate_limited")
                if response.status_code != 200:
                    return LlmResult("unavailable", reason="provider_error")
                body = bytearray()
                async for block in response.aiter_bytes():
                    if len(body) + len(block) > MAX_HTTP_RESPONSE_BYTES:
                        return LlmResult("invalid", reason="output_budget")
                    body.extend(block)
            parsed = _Response.model_validate_json(body)
            if (
                not parsed.done
                or parsed.done_reason == "length"
                or parsed.eval_count > request.max_output_tokens
            ):
                return LlmResult("invalid", reason="output_budget")
            if parsed.message.role != "assistant" or parsed.message.tool_calls:
                return LlmResult("invalid", reason="unexpected_response")
            if not parsed.message.content.strip():
                return LlmResult("unavailable", reason="empty_or_refused")
            AiOutputDto.model_validate_json(parsed.message.content)
            return LlmResult(
                "available",
                parsed.message.content,
                parsed.prompt_eval_count,
                parsed.eval_count,
            )
        except httpx.TimeoutException:
            return LlmResult("unavailable", reason="timeout")
        except httpx.HTTPError:
            return LlmResult("unavailable", reason="provider_error")
        except (ValidationError, ValueError, json.JSONDecodeError):
            return LlmResult("invalid", reason="invalid_schema")
