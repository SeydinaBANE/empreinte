"""Test d'integration du RAG Qdrant (necessite un Qdrant joignable + fastembed).

Exclu par defaut (`-m "not integration"`). Lancer avec :
    EMPREINTE_QDRANT_URL=http://localhost:6333 pytest -m integration
"""

from __future__ import annotations

import os

import pytest

from empreinte.corpus import ESRS_CORPUS
from empreinte.retriever import QdrantRetriever

pytestmark = pytest.mark.integration


async def test_index_then_retrieve() -> None:
    url = os.environ.get("EMPREINTE_QDRANT_URL")
    if not url:
        pytest.skip("EMPREINTE_QDRANT_URL non defini")
    qdrant = pytest.importorskip("qdrant_client")

    collection = "empreinte_esrs_test"
    client = qdrant.AsyncQdrantClient(url=url)
    await client.add(
        collection_name=collection,
        documents=[doc.text for doc in ESRS_CORPUS],
        metadata=[{"datapoint": doc.datapoint.value} for doc in ESRS_CORPUS],
        ids=list(range(1, len(ESRS_CORPUS) + 1)),
    )
    await client.close()

    retriever = QdrantRetriever(url=url, collection=collection)
    passages = await retriever.retrieve("emissions de gaz a effet de serre", top_k=2)
    assert passages
    assert passages[0].score > 0
