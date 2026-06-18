"""Composition root : assemble gateway vision, extraction, moteur carbone, RAG et assistant.

L'assemblage par defaut est entierement hors-ligne (provider deterministe + corpus en
memoire + document de demo) afin que l'application demarre sans dependance externe ; en
production on injecte un VLM via vLLM/Ollama et un retriever Qdrant.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from empreinte.assistant import RegulatoryAssistant
from empreinte.config import Settings, get_settings
from empreinte.extraction import Extractor
from empreinte.factors import CarbonEngine
from empreinte.gateway import (
    LLMGateway,
    LocalVisionProvider,
    OpenAICompatVisionProvider,
    _build_async_http_client,
)
from empreinte.governance import assert_sovereign_endpoint
from empreinte.report import ReportBuilder
from empreinte.retriever import InMemoryRetriever, QdrantRetriever, RegulatoryDoc, Retriever
from empreinte.schemas import DocumentPage, EsrsDatapoint, SourceDocument

_clients: list[httpx.AsyncClient] = []

_DEMO_PIXEL = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYP"
    "hfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

_DEMO_EXTRACTION_JSON = (
    "["
    '{"category": "electricity", "value": 12000, "unit": "kWh", "source_page": 1,'
    ' "raw_excerpt": "Consommation electrique annuelle 12 000 kWh", "confidence": 0.95},'
    '{"category": "natural_gas", "value": 4500, "unit": "kWh", "source_page": 1,'
    ' "raw_excerpt": "Gaz naturel 4 500 kWh", "confidence": 0.9},'
    '{"category": "business_travel_car", "value": 8200, "unit": "km", "source_page": 2,'
    ' "raw_excerpt": "Deplacements professionnels 8 200 km", "confidence": 0.85},'
    '{"category": "waste", "value": 1500, "unit": "kg", "source_page": 2,'
    ' "raw_excerpt": "Dechets non dangereux 1 500 kg", "confidence": 0.8}'
    "]"
)

_ESRS_CORPUS: list[RegulatoryDoc] = [
    RegulatoryDoc(
        doc_id="esrs-e1-5",
        datapoint=EsrsDatapoint.E1_5_ENERGY,
        text=(
            "ESRS E1-5 impose de declarer la consommation energetique totale en MWh, ventilee "
            "par sources renouvelables et non renouvelables, ainsi que le mix energetique."
        ),
    ),
    RegulatoryDoc(
        doc_id="esrs-e1-6",
        datapoint=EsrsDatapoint.E1_6_GHG,
        text=(
            "ESRS E1-6 impose de declarer les emissions brutes de gaz a effet de serre des "
            "scopes 1, 2 et 3 en tonnes equivalent CO2, et les emissions totales consolidees."
        ),
    ),
    RegulatoryDoc(
        doc_id="ghg-scopes",
        datapoint=EsrsDatapoint.E1_6_GHG,
        text=(
            "Le scope 2 couvre les emissions indirectes liees a l'energie achetee et consommee "
            "(electricite, chaleur, vapeur). Le scope 1 couvre les emissions directes."
        ),
    ),
]


@dataclass(frozen=True)
class Pipeline:
    """Composants assembles de l'application."""

    extractor: Extractor
    report_builder: ReportBuilder
    assistant: RegulatoryAssistant
    documents: DocumentStore


class DocumentStore:
    """Stockage en memoire des documents uploades (aucune persistance externe)."""

    def __init__(self) -> None:
        self._documents: dict[str, SourceDocument] = {}

    def add(self, document: SourceDocument) -> None:
        self._documents[document.doc_id] = document

    def get(self, doc_id: str) -> SourceDocument | None:
        return self._documents.get(doc_id)


def _demo_document() -> SourceDocument:
    pages = [
        DocumentPage(page_number=1, image_base64=_DEMO_PIXEL),
        DocumentPage(page_number=2, image_base64=_DEMO_PIXEL),
    ]
    return SourceDocument(
        doc_id="demo-facture-energie", title="Facture energie (demo)", pages=pages
    )


def _build_gateway(cfg: Settings) -> LLMGateway:
    if not cfg.llm_api_base:
        return LLMGateway(
            primary=LocalVisionProvider(
                model=cfg.llm_model_primary, extraction_json=_DEMO_EXTRACTION_JSON
            ),
            fallback=LocalVisionProvider(
                model=cfg.llm_model_fallback, extraction_json=_DEMO_EXTRACTION_JSON
            ),
        )
    assert_sovereign_endpoint(cfg.llm_api_base, cfg.sovereign_mode)
    client = _build_async_http_client(cfg)
    _clients.append(client)
    return LLMGateway(
        primary=OpenAICompatVisionProvider(model=cfg.llm_model_primary, client=client),
        fallback=OpenAICompatVisionProvider(model=cfg.llm_model_fallback, client=client),
    )


def _build_retriever(cfg: Settings) -> Retriever:
    if cfg.qdrant_url:
        return QdrantRetriever(url=cfg.qdrant_url, collection=cfg.qdrant_collection)
    return InMemoryRetriever(_ESRS_CORPUS)


def build_pipeline() -> Pipeline:
    """Assemble le pipeline complet selon la configuration (demo hors-ligne par defaut)."""
    cfg = get_settings()
    gateway = _build_gateway(cfg)
    retriever = _build_retriever(cfg)
    engine = CarbonEngine()
    store = DocumentStore()
    store.add(_demo_document())
    return Pipeline(
        extractor=Extractor(gateway),
        report_builder=ReportBuilder(engine, gateway, cfg.reporting_year),
        assistant=RegulatoryAssistant(gateway, retriever),
        documents=store,
    )


async def _cleanup() -> None:
    """Ferme les clients HTTP async acquis (arret gracieux)."""
    while _clients:
        client = _clients.pop()
        await client.aclose()
