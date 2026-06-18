"""Tests du retriever lexical en memoire."""

from __future__ import annotations

import pytest

from empreinte.retriever import InMemoryRetriever, RegulatoryDoc
from empreinte.schemas import EsrsDatapoint


@pytest.fixture
def retriever() -> InMemoryRetriever:
    return InMemoryRetriever(
        [
            RegulatoryDoc("e1-5", EsrsDatapoint.E1_5_ENERGY, "consommation energetique totale MWh"),
            RegulatoryDoc("e1-6", EsrsDatapoint.E1_6_GHG, "emissions gaz effet de serre scopes"),
        ]
    )


async def test_retrieve_ranks_by_overlap(retriever: InMemoryRetriever) -> None:
    passages = await retriever.retrieve("emissions de gaz", top_k=2)
    assert passages[0].doc_id == "e1-6"


async def test_retrieve_empty_query_returns_nothing(retriever: InMemoryRetriever) -> None:
    assert await retriever.retrieve("   ", top_k=2) == []


async def test_retrieve_respects_top_k(retriever: InMemoryRetriever) -> None:
    passages = await retriever.retrieve("consommation emissions", top_k=1)
    assert len(passages) == 1
