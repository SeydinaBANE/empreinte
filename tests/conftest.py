"""Fixtures partagees : provider vision scriptable et echantillons deterministes."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from empreinte.gateway import LLMGateway
from empreinte.schemas import (
    ActivityCategory,
    ActivityUnit,
    DocumentPage,
    ExtractedIndicator,
    LLMRequest,
    SourceDocument,
)

_PIXEL = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


class ScriptedVisionProvider:
    """Provider qui renvoie une reponse predefinie (tests deterministes)."""

    def __init__(self, model: str, reply: str) -> None:
        self.model = model
        self._reply = reply

    async def complete(self, request: LLMRequest) -> str:
        del request
        return self._reply

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        del request
        for word in self._reply.split():
            yield word


def make_gateway(reply: str) -> LLMGateway:
    """Construit une gateway dont le primaire renvoie toujours ``reply``."""
    provider = ScriptedVisionProvider(model="scripted", reply=reply)
    return LLMGateway(primary=provider, fallback=provider)


@pytest.fixture
def demo_document() -> SourceDocument:
    """Document a deux pages, images factices (le contenu importe peu en tests)."""
    return SourceDocument(
        doc_id="doc-test",
        title="Facture test",
        pages=[
            DocumentPage(page_number=1, image_base64=_PIXEL),
            DocumentPage(page_number=2, image_base64=_PIXEL),
        ],
    )


@pytest.fixture
def indicators() -> list[ExtractedIndicator]:
    """Indicateurs d'activite couvrant les trois scopes."""
    return [
        ExtractedIndicator(
            category=ActivityCategory.ELECTRICITY,
            value=12000,
            unit=ActivityUnit.KWH,
            source_page=1,
        ),
        ExtractedIndicator(
            category=ActivityCategory.NATURAL_GAS,
            value=4500,
            unit=ActivityUnit.KWH,
            source_page=1,
        ),
        ExtractedIndicator(
            category=ActivityCategory.BUSINESS_TRAVEL_CAR,
            value=8200,
            unit=ActivityUnit.KM,
            source_page=2,
        ),
    ]
