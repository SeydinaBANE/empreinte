"""Tests de la gateway LLM vision (provider local, fallback, provider HTTP)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx
import pytest

from empreinte.gateway import (
    CircuitBreaker,
    FailingProvider,
    LLMGateway,
    LLMProviderError,
    LocalVisionProvider,
    OpenAICompatVisionProvider,
)
from empreinte.schemas import ImageContent, LLMRequest, Message, Role


class _CountingFailingProvider:
    """Primaire qui echoue toujours et compte ses appels (test du disjoncteur)."""

    def __init__(self, model: str = "primary") -> None:
        self.model = model
        self.calls = 0

    async def complete(self, request: LLMRequest) -> str:
        del request
        self.calls += 1
        raise LLMProviderError("indisponible")

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        del request
        raise LLMProviderError("indisponible")
        yield  # pragma: no cover


_PIXEL = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def _text_request(text: str) -> LLMRequest:
    return LLMRequest(messages=[Message(role=Role.USER, content=text)])


def _image_request() -> LLMRequest:
    return LLMRequest(
        messages=[Message(role=Role.USER, content="extrais", images=[ImageContent(base64=_PIXEL)])]
    )


async def test_local_provider_returns_json_for_images() -> None:
    provider = LocalVisionProvider(model="m", extraction_json="[1]", text_reply="texte")
    assert await provider.complete(_image_request()) == "[1]"


async def test_local_provider_returns_text_without_images() -> None:
    provider = LocalVisionProvider(model="m", extraction_json="[1]", text_reply="texte")
    assert await provider.complete(_text_request("bonjour")) == "texte"


async def test_gateway_falls_back_on_primary_failure() -> None:
    gateway = LLMGateway(
        primary=FailingProvider(model="primary"),
        fallback=LocalVisionProvider(model="fallback", text_reply="secours"),
    )
    response = await gateway.complete(_text_request("q"))
    assert response.used_fallback is True
    assert response.content == "secours"


async def test_openai_compat_complete_parses_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "vlm"
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://local")
    provider = OpenAICompatVisionProvider(model="vlm", client=client)
    assert await provider.complete(_text_request("q")) == "ok"
    await client.aclose()


async def test_openai_compat_sends_multimodal_content() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://local")
    provider = OpenAICompatVisionProvider(model="vlm", client=client)
    await provider.complete(_image_request())
    parts = captured["body"]["messages"][0]["content"]  # type: ignore[index]
    assert any(part["type"] == "image_url" for part in parts)
    await client.aclose()


async def test_openai_compat_sends_guided_json_schema() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "[]"}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://local")
    provider = OpenAICompatVisionProvider(model="vlm", client=client)
    request = LLMRequest(
        messages=[Message(role=Role.USER, content="q")],
        response_schema={"type": "array"},
    )
    await provider.complete(request)
    assert captured["body"]["guided_json"] == {"type": "array"}  # type: ignore[index]
    await client.aclose()


async def test_openai_compat_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://local")
    provider = OpenAICompatVisionProvider(model="vlm", client=client)
    from empreinte.gateway import LLMProviderError

    with pytest.raises(LLMProviderError):
        await provider.complete(_text_request("q"))
    await client.aclose()


def test_circuit_breaker_opens_after_threshold() -> None:
    clock = {"t": 0.0}
    breaker = CircuitBreaker(threshold=2, reset_sec=10.0, clock=lambda: clock["t"])
    assert breaker.allow() is True
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_open is True
    assert breaker.allow() is False


def test_circuit_breaker_half_opens_after_reset() -> None:
    clock = {"t": 0.0}
    breaker = CircuitBreaker(threshold=1, reset_sec=10.0, clock=lambda: clock["t"])
    breaker.record_failure()
    assert breaker.allow() is False
    clock["t"] = 11.0
    assert breaker.allow() is True


def test_circuit_breaker_success_resets() -> None:
    breaker = CircuitBreaker(threshold=2, reset_sec=10.0)
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    assert breaker.is_open is False


async def test_gateway_short_circuits_primary_when_open() -> None:
    primary = _CountingFailingProvider()
    breaker = CircuitBreaker(threshold=1, reset_sec=100.0)
    gateway = LLMGateway(
        primary=primary,
        fallback=LocalVisionProvider(model="fb", text_reply="secours"),
        breaker=breaker,
    )
    first = await gateway.complete(_text_request("q"))
    assert first.used_fallback is True
    assert primary.calls == 1
    second = await gateway.complete(_text_request("q"))
    assert second.used_fallback is True
    assert primary.calls == 1  # disjoncteur ouvert : primaire non rappele


async def test_openai_compat_stream_yields_tokens() -> None:
    sse = 'data: {"choices":[{"delta":{"content":"hel"}}]}\n\ndata: {"choices":[{"delta":{"content":"lo"}}]}\n\ndata: [DONE]\n\n'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse.encode())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://local")
    provider = OpenAICompatVisionProvider(model="vlm", client=client)
    tokens = [token async for token in provider.stream(_text_request("q"))]
    assert "".join(tokens) == "hello"
    await client.aclose()
