"""Assistant reglementaire : repond aux questions ESRS en s'ancrant sur le corpus RAG."""

from __future__ import annotations

from collections.abc import AsyncIterator

from empreinte.gateway import LLMGateway
from empreinte.retriever import Retriever
from empreinte.schemas import ChatAnswer, LLMRequest, Message, RetrievedPassage, Role

_SYSTEM = (
    "Tu es un assistant CSRD/ESRS. Reponds en francais, de maniere concise, en t'appuyant "
    "uniquement sur les passages reglementaires fournis. Si l'information est absente, dis-le."
)


def _build_request(question: str, passages: list[RetrievedPassage]) -> LLMRequest:
    context = "\n".join(f"[{p.doc_id}] {p.text}" for p in passages) or "(aucun passage)"
    prompt = f"Passages:\n{context}\n\nQuestion: {question}"
    return LLMRequest(
        messages=[
            Message(role=Role.SYSTEM, content=_SYSTEM),
            Message(role=Role.USER, content=prompt),
        ]
    )


class RegulatoryAssistant:
    """Repond aux questions reglementaires via retrieval + synthese LLM."""

    def __init__(self, gateway: LLMGateway, retriever: Retriever, top_k: int = 3) -> None:
        self._gateway = gateway
        self._retriever = retriever
        self._top_k = top_k

    async def answer(self, question: str) -> ChatAnswer:
        """Retrouve les passages pertinents puis synthetise une reponse sourcée."""
        passages = await self._retriever.retrieve(question, self._top_k)
        response = await self._gateway.complete(_build_request(question, passages))
        answer = response.content.strip() or self._fallback(passages)
        return ChatAnswer(answer=answer, passages=passages, used_fallback=response.used_fallback)

    async def answer_stream(self, question: str) -> AsyncIterator[str]:
        """Diffuse la reponse en flux (SSE), apres retrieval."""
        passages = await self._retriever.retrieve(question, self._top_k)
        async for token in self._gateway.stream(_build_request(question, passages)):
            yield token

    @staticmethod
    def _fallback(passages: list[RetrievedPassage]) -> str:
        if not passages:
            return "Aucun passage reglementaire pertinent n'a ete trouve."
        return passages[0].text
