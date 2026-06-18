"""Gateway LLM vision : abstraction du fournisseur multimodal avec fallback.

La gateway ne connait pas le fournisseur concret : elle manipule un ``VisionLLMProvider``
(Protocol). En mode souverain on injecte ``OpenAICompatVisionProvider`` pointant vers un
serveur local (vLLM/Ollama) servant un VLM open-source ; ``LocalVisionProvider`` deterministe
permet de tourner hors-ligne et en tests sans aucun appel reseau.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Protocol

import httpx

from empreinte.config import Settings, get_settings
from empreinte.logging import get_logger
from empreinte.observability import METRICS, record_span
from empreinte.schemas import LLMRequest, LLMResponse, Message

logger = get_logger(__name__)

_ContentPart = dict[str, object]


class LLMProviderError(RuntimeError):
    """Echec d'appel d'un fournisseur LLM."""


class VisionLLMProvider(Protocol):
    """Contrat minimal d'un fournisseur LLM multimodal asynchrone."""

    model: str

    async def complete(self, request: LLMRequest) -> str:
        """Retourne la completion textuelle pour la requete fournie."""
        ...

    async def stream(self, _request: LLMRequest) -> AsyncIterator[str]:
        """Diffuse la completion token par token."""
        ...
        yield ""


class LocalVisionProvider:
    """Fournisseur deterministe hors-ligne (tests et mode local).

    Les requetes multimodales (avec images) renvoient ``extraction_json`` ; les requetes
    purement textuelles renvoient ``text_reply``.
    """

    def __init__(self, model: str, extraction_json: str = "[]", text_reply: str = "") -> None:
        self.model = model
        self._extraction_json = extraction_json
        self._text_reply = text_reply

    @staticmethod
    def _has_images(request: LLMRequest) -> bool:
        return any(message.images for message in request.messages)

    async def complete(self, request: LLMRequest) -> str:
        if self._has_images(request):
            return self._extraction_json
        return self._text_reply

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        result = await self.complete(request)
        for word in result.split():
            yield word


class FailingProvider:
    """Fournisseur qui echoue systematiquement (utile pour tester le fallback)."""

    def __init__(self, model: str) -> None:
        self.model = model

    async def complete(self, request: LLMRequest) -> str:
        del request
        raise LLMProviderError(f"provider {self.model} indisponible")

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        del request
        raise LLMProviderError(f"provider {self.model} indisponible")
        yield  # pragma: no cover


class OpenAICompatVisionProvider:
    """Provider HTTP compatible chat completions OpenAI, avec contenu multimodal."""

    def __init__(
        self, model: str, client: httpx.AsyncClient, path: str = "/chat/completions"
    ) -> None:
        self.model = model
        self._client = client
        self._path = path

    @staticmethod
    def _content(message: Message) -> str | list[_ContentPart]:
        if not message.images:
            return message.content
        parts: list[_ContentPart] = [{"type": "text", "text": message.content}]
        for image in message.images:
            data_url = f"data:{image.media_type};base64,{image.base64}"
            parts.append({"type": "image_url", "image_url": {"url": data_url}})
        return parts

    def _build_payload(self, request: LLMRequest) -> dict[str, object]:
        return {
            "model": self.model,
            "messages": [
                {"role": m.role.value, "content": self._content(m)} for m in request.messages
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

    async def complete(self, request: LLMRequest) -> str:
        payload = self._build_payload(request)
        try:
            response = await self._client.post(self._path, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"appel LLM {self.model} echoue: {exc}") from exc
        try:
            return str(response.json()["choices"][0]["message"]["content"])
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMProviderError(f"reponse LLM {self.model} invalide: {exc}") from exc

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        payload = self._build_payload(request)
        payload["stream"] = True
        try:
            async with self._client.stream("POST", self._path, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    token = self._parse_sse_line(line)
                    if token:
                        yield token
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"stream LLM {self.model} echoue: {exc}") from exc

    @staticmethod
    def _parse_sse_line(line: str) -> str:
        line = line.strip()
        if not line or line == "data: [DONE]" or not line.startswith("data: "):
            return ""
        chunk = json.loads(line[6:])
        delta = chunk.get("choices", [{}])[0].get("delta", {})
        content: str = delta.get("content", "")
        return content


class LLMGateway:
    """Route vers le provider primaire, bascule sur le secondaire en cas d'echec."""

    def __init__(self, primary: VisionLLMProvider, fallback: VisionLLMProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Appelle le primaire puis le fallback ; leve ``LLMProviderError`` si les deux echouent."""
        with record_span("llm.primary", model=self._primary.model):
            try:
                content = await self._primary.complete(request)
                METRICS.incr("llm.primary.success")
                return LLMResponse(content=content, model=self._primary.model)
            except LLMProviderError as exc:
                METRICS.incr("llm.primary.failure")
                logger.warning("primary_failed", model=self._primary.model, error=str(exc))

        with record_span("llm.fallback", model=self._fallback.model):
            content = await self._fallback.complete(request)
            METRICS.incr("llm.fallback.success")
            return LLMResponse(content=content, model=self._fallback.model, used_fallback=True)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Diffuse la completion depuis le primaire, avec fallback sur le secondaire."""
        tried_primary = False
        try:
            with record_span("llm.primary", model=self._primary.model):
                async for token in self._primary.stream(request):
                    tried_primary = True
                    yield token
                METRICS.incr("llm.primary.success")
                return
        except LLMProviderError as exc:
            METRICS.incr("llm.primary.failure")
            logger.warning("primary_failed", model=self._primary.model, error=str(exc))
            if not tried_primary:
                with record_span("llm.fallback", model=self._fallback.model):
                    async for token in self._fallback.stream(request):
                        yield token
                    METRICS.incr("llm.fallback.success")


def _build_async_http_client(cfg: Settings) -> httpx.AsyncClient:
    """Construit le client HTTP async du provider LLM."""
    headers = {"Authorization": f"Bearer {cfg.llm_api_key}"} if cfg.llm_api_key else {}
    return httpx.AsyncClient(
        base_url=cfg.llm_api_base, headers=headers, timeout=cfg.llm_timeout_sec
    )


def build_default_gateway(
    settings: Settings | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> LLMGateway:
    """Construit la gateway selon la configuration.

    Si ``llm_api_base`` est renseigne, utilise un provider HTTP reel (vLLM/Ollama) ; sinon,
    retombe sur ``LocalVisionProvider`` deterministe pour fonctionner hors-ligne.
    """
    cfg = settings or get_settings()
    if not cfg.llm_api_base:
        return LLMGateway(
            primary=LocalVisionProvider(model=cfg.llm_model_primary),
            fallback=LocalVisionProvider(model=cfg.llm_model_fallback),
        )
    client = http_client or _build_async_http_client(cfg)
    return LLMGateway(
        primary=OpenAICompatVisionProvider(model=cfg.llm_model_primary, client=client),
        fallback=OpenAICompatVisionProvider(model=cfg.llm_model_fallback, client=client),
    )
