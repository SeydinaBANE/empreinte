"""Tests de la composition root et du stockage documentaire."""

from __future__ import annotations

from empreinte.config import Settings
from empreinte.gateway import LLMGateway
from empreinte.retriever import InMemoryRetriever, QdrantRetriever
from empreinte.schemas import DocumentPage, SourceDocument
from empreinte.services import (
    DocumentStore,
    _build_gateway,
    _build_retriever,
    build_pipeline,
)


def test_document_store_add_and_get() -> None:
    store = DocumentStore()
    doc = SourceDocument(
        doc_id="x", title="t", pages=[DocumentPage(page_number=1, image_base64="aaa")]
    )
    store.add(doc)
    assert store.get("x") is doc
    assert store.get("missing") is None


def test_build_pipeline_seeds_demo_document() -> None:
    pipeline = build_pipeline()
    demo = pipeline.documents.get("demo-facture-energie")
    assert demo is not None
    assert demo.page_count == 2


async def test_demo_pipeline_extracts_canned_indicators() -> None:
    pipeline = build_pipeline()
    demo = pipeline.documents.get("demo-facture-energie")
    assert demo is not None
    result = await pipeline.extractor.extract(demo)
    assert len(result.indicators) == 4


def test_build_gateway_local_when_no_api_base() -> None:
    assert isinstance(_build_gateway(Settings(llm_api_base="")), LLMGateway)


def test_build_gateway_http_when_api_base_local() -> None:
    gateway = _build_gateway(Settings(llm_api_base="http://localhost:9000/v1"))
    assert isinstance(gateway, LLMGateway)


def test_build_retriever_inmemory_by_default() -> None:
    assert isinstance(_build_retriever(Settings(qdrant_url="")), InMemoryRetriever)


def test_build_retriever_qdrant_when_url_set() -> None:
    retriever = _build_retriever(Settings(qdrant_url="http://localhost:6333"))
    assert isinstance(retriever, QdrantRetriever)
