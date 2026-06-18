"""Extraction multimodale : un VLM lit les pages et renvoie des donnees d'activite.

Le modele se limite a l'extraction structuree (categorie, valeur, unite, page-source) ;
le calcul carbone est delegue au moteur deterministe. La sortie attendue est un tableau
JSON, parse defensivement et rattache a la taxonomie ESRS.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from empreinte.config import get_settings
from empreinte.gateway import LLMGateway
from empreinte.logging import get_logger
from empreinte.observability import METRICS, record_span
from empreinte.schemas import (
    ExtractedIndicator,
    ExtractedIndicatorDraft,
    ExtractionResult,
    ImageContent,
    LLMRequest,
    Message,
    Role,
    SourceDocument,
)
from empreinte.taxonomy import map_indicator

logger = get_logger(__name__)


def extraction_schema() -> dict[str, object]:
    """Schema JSON (tableau d'indicateurs) pour le guided decoding du VLM."""
    return {"type": "array", "items": ExtractedIndicatorDraft.model_json_schema()}


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

    def __init__(self, gateway: LLMGateway, min_confidence: float | None = None) -> None:
        self._gateway = gateway
        cfg = get_settings()
        self._min_confidence = (
            cfg.extraction_min_confidence if min_confidence is None else min_confidence
        )
        self._guided = cfg.llm_guided_decoding

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
            ],
            response_schema=extraction_schema() if self._guided else None,
        )

    async def extract(self, document: SourceDocument) -> ExtractionResult:
        """Extrait, rattache a l'ESRS et marque les indicateurs peu fiables."""
        with record_span("extraction.vision", doc_id=document.doc_id):
            response = await self._gateway.complete(self._build_request(document))
        indicators = [self._finalize(draft) for draft in self._parse(response.content)]
        METRICS.incr("extraction.indicators", len(indicators))
        flagged = sum(1 for indicator in indicators if indicator.needs_review)
        logger.info(
            "extraction_done", doc_id=document.doc_id, count=len(indicators), flagged=flagged
        )
        return ExtractionResult(doc_id=document.doc_id, indicators=indicators)

    def _finalize(self, draft: ExtractedIndicatorDraft) -> ExtractedIndicator:
        indicator = ExtractedIndicator(
            **draft.model_dump(), needs_review=draft.confidence < self._min_confidence
        )
        return map_indicator(indicator)

    @staticmethod
    def _parse(content: str) -> list[ExtractedIndicatorDraft]:
        payload = _isolate_json_array(content)
        try:
            raw_items = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"JSON d'extraction invalide: {exc}") from exc
        if not isinstance(raw_items, list):
            raise ExtractionError("le JSON d'extraction n'est pas un tableau")
        drafts: list[ExtractedIndicatorDraft] = []
        for item in raw_items:
            try:
                drafts.append(ExtractedIndicatorDraft.model_validate(item))
            except ValidationError as exc:
                METRICS.incr("extraction.rejected")
                logger.warning("indicator_rejected", error=str(exc))
        return drafts


def _isolate_json_array(content: str) -> str:
    """Extrait le premier tableau JSON d'une reponse, tolere les fences markdown."""
    start = content.find("[")
    end = content.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ExtractionError("aucun tableau JSON trouve dans la reponse")
    return content[start : end + 1]
