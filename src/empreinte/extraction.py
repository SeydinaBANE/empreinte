"""Extraction multimodale : un VLM lit les pages et renvoie des donnees d'activite.

Le modele se limite a l'extraction structuree (categorie, valeur, unite, page-source) ;
le calcul carbone est delegue au moteur deterministe. La sortie attendue est un tableau
JSON, parse defensivement et rattache a la taxonomie ESRS.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from empreinte.gateway import LLMGateway
from empreinte.logging import get_logger
from empreinte.observability import METRICS, record_span
from empreinte.schemas import (
    ExtractedIndicator,
    ExtractionResult,
    ImageContent,
    LLMRequest,
    Message,
    Role,
    SourceDocument,
)
from empreinte.taxonomy import map_indicator

logger = get_logger(__name__)

_VALID_CATEGORIES = (
    "electricity, natural_gas, district_heating, diesel, petrol, business_travel_car, waste"
)
_VALID_UNITS = "kWh, MWh, L, m3, kg, t, km, EUR"

_SYSTEM_PROMPT = (
    "Tu es un extracteur de donnees ESG. A partir des images de pages fournies, extrais "
    "uniquement les donnees d'activite environnementales (energie, carburants, deplacements, "
    "dechets). Reponds STRICTEMENT par un tableau JSON, sans texte autour. Chaque element : "
    '{"category": <une de: ' + _VALID_CATEGORIES + ">, "
    '"value": <nombre>, "unit": <une de: ' + _VALID_UNITS + ">, "
    '"source_page": <entier>, "raw_excerpt": <texte court cite>, "confidence": <0..1>}. '
    "N'invente aucune valeur : si rien n'est lisible, renvoie []."
)


class ExtractionError(RuntimeError):
    """Reponse d'extraction non exploitable (JSON absent ou invalide)."""


class Extractor:
    """Orchestre l'appel vision et transforme la reponse en indicateurs structures."""

    def __init__(self, gateway: LLMGateway) -> None:
        self._gateway = gateway

    def _build_request(self, document: SourceDocument) -> LLMRequest:
        images = [
            ImageContent(base64=page.image_base64, media_type=page.media_type)
            for page in document.pages
        ]
        instruction = (
            f"Document '{document.title}' ({document.page_count} page(s)). "
            "Extrais les donnees d'activite environnementales de chaque page."
        )
        return LLMRequest(
            messages=[
                Message(role=Role.SYSTEM, content=_SYSTEM_PROMPT),
                Message(role=Role.USER, content=instruction, images=images),
            ]
        )

    async def extract(self, document: SourceDocument) -> ExtractionResult:
        """Extrait et rattache les indicateurs d'activite d'un document."""
        with record_span("extraction.vision", doc_id=document.doc_id):
            response = await self._gateway.complete(self._build_request(document))
        indicators = [map_indicator(item) for item in self._parse(response.content)]
        METRICS.incr("extraction.indicators", len(indicators))
        logger.info("extraction_done", doc_id=document.doc_id, count=len(indicators))
        return ExtractionResult(doc_id=document.doc_id, indicators=indicators)

    @staticmethod
    def _parse(content: str) -> list[ExtractedIndicator]:
        payload = _isolate_json_array(content)
        try:
            raw_items = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"JSON d'extraction invalide: {exc}") from exc
        if not isinstance(raw_items, list):
            raise ExtractionError("le JSON d'extraction n'est pas un tableau")
        indicators: list[ExtractedIndicator] = []
        for item in raw_items:
            try:
                indicators.append(ExtractedIndicator.model_validate(item))
            except ValidationError as exc:
                METRICS.incr("extraction.rejected")
                logger.warning("indicator_rejected", error=str(exc))
        return indicators


def _isolate_json_array(content: str) -> str:
    """Extrait le premier tableau JSON d'une reponse, tolere les fences markdown."""
    start = content.find("[")
    end = content.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ExtractionError("aucun tableau JSON trouve dans la reponse")
    return content[start : end + 1]
