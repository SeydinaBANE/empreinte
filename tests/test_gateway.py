"""Tests de la gateway LLM vision (provider local, fallback, provider HTTP)."""

from __future__ import annotations

import json

import httpx
import pytest

from empreinte.gateway import (
    FailingProvider,
    LLMGateway,
    LocalVisionProvider,
    OpenAICompatVisionProvider,
)
from empreinte.schemas import ImageContent, LLMRequest, Message, Role

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


async def test_openai_compat_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://local")
    provider = OpenAICompatVisionProvider(model="vlm", client=client)
    from empreinte.gateway import LLMProviderError

    with pytest.raises(LLMProviderError):
        await provider.complete(_text_request("q"))
    await client.aclose()


async def test_openai_compat_stream_yields_tokens() -> None:
    sse = 'data: {"choices":[{"delta":{"content":"hel"}}]}\n\ndata: {"choices":[{"delta":{"content":"lo"}}]}\n\ndata: [DONE]\n\n'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse.encode())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://local")
    provider = OpenAICompatVisionProvider(model="vlm", client=client)
    tokens = [token async for token in provider.stream(_text_request("q"))]
    assert "".join(tokens) == "hello"
    await client.aclose()
