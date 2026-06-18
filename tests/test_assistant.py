"""Tests de l'assistant reglementaire RAG."""

from __future__ import annotations

from empreinte.assistant import RegulatoryAssistant
from empreinte.retriever import InMemoryRetriever, RegulatoryDoc
from empreinte.schemas import EsrsDatapoint
from tests.conftest import make_gateway


def _retriever() -> InMemoryRetriever:
    return InMemoryRetriever(
        [RegulatoryDoc("e1-6", EsrsDatapoint.E1_6_GHG, "emissions scope 2 energie achetee")]
    )


async def test_answer_returns_passages() -> None:
    assistant = RegulatoryAssistant(
        make_gateway("Le scope 2 couvre l'energie achetee."), _retriever()
    )
    answer = await assistant.answer("Que couvre le scope 2 ?")
    assert "scope 2" in answer.answer
    assert answer.passages[0].doc_id == "e1-6"


async def test_answer_falls_back_to_passage_when_llm_silent() -> None:
    assistant = RegulatoryAssistant(make_gateway(""), _retriever())
    answer = await assistant.answer("scope 2 energie")
    assert "energie achetee" in answer.answer


async def test_answer_stream_yields_tokens() -> None:
    assistant = RegulatoryAssistant(make_gateway("un deux trois"), _retriever())
    tokens = [token async for token in assistant.answer_stream("scope")]
    assert tokens == ["un", "deux", "trois"]
