"""RAG reglementaire : retrouve les passages ESRS pertinents pour ancrer une reponse.

``InMemoryRetriever`` (scoring lexical, hors-ligne) sert le mode demo et les tests ;
``QdrantRetriever`` sert la production. Les deux respectent le Protocol ``Retriever``.
"""

from __future__ import annotations

import re
from typing import Protocol

from empreinte.observability import record_span
from empreinte.schemas import EsrsDatapoint, RetrievedPassage

_TOKEN = re.compile(r"\w+")


class RegulatoryDoc:
    """Extrait du corpus reglementaire ESRS, rattache a un point de donnee."""

    def __init__(self, doc_id: str, datapoint: EsrsDatapoint, text: str) -> None:
        self.doc_id = doc_id
        self.datapoint = datapoint
        self.text = text


class Retriever(Protocol):
    """Contrat d'un retriever de passages reglementaires."""

    async def retrieve(self, query: str, top_k: int) -> list[RetrievedPassage]:
        """Retourne les ``top_k`` passages les plus pertinents pour la requete."""
        ...


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN.findall(text)}


class InMemoryRetriever:
    """Retriever lexical en memoire (recouvrement de tokens), sans dependance externe."""

    def __init__(self, documents: list[RegulatoryDoc]) -> None:
        self._documents = documents

    async def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedPassage]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []
        scored: list[RetrievedPassage] = []
        with record_span("retriever.inmemory", query_len=str(len(query))):
            for doc in self._documents:
                overlap = len(query_tokens & _tokenize(doc.text))
                if overlap == 0:
                    continue
                score = overlap / len(query_tokens)
                scored.append(
                    RetrievedPassage(
                        doc_id=doc.doc_id,
                        datapoint=doc.datapoint,
                        text=doc.text,
                        score=round(score, 3),
                    )
                )
        scored.sort(key=lambda passage: passage.score, reverse=True)
        return scored[:top_k]


class QdrantRetriever:
    """Retriever vectoriel Qdrant (production)."""

    def __init__(self, url: str, collection: str) -> None:
        self._url = url
        self._collection = collection

    async def retrieve(
        self, query: str, top_k: int = 3
    ) -> list[RetrievedPassage]:  # pragma: no cover - depend de Qdrant
        from qdrant_client import AsyncQdrantClient

        client = AsyncQdrantClient(url=self._url)
        try:
            hits = await client.query(
                collection_name=self._collection, query_text=query, limit=top_k
            )
        finally:
            await client.close()
        return [
            RetrievedPassage(
                doc_id=str(hit.id),
                datapoint=EsrsDatapoint(hit.metadata.get("datapoint", EsrsDatapoint.UNMAPPED)),
                text=str(hit.document),
                score=float(hit.score),
            )
            for hit in hits
        ]
