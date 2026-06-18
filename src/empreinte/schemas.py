"""Schemas partages : pages, indicateurs ESG, facteurs d'emission et rapport carbone."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    """Role d'un message dans une conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ImageContent(BaseModel):
    """Image jointe a un message multimodal (encodee en base64)."""

    base64: str
    media_type: str = "image/png"


class Message(BaseModel):
    """Message echange avec le LLM, eventuellement multimodal."""

    role: Role
    content: str
    images: list[ImageContent] = Field(default_factory=list)


class LLMRequest(BaseModel):
    """Requete adressee a la gateway LLM (vision)."""

    messages: list[Message]
    max_tokens: int = Field(default=1536, ge=1, le=8192)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class LLMResponse(BaseModel):
    """Reponse renvoyee par la gateway LLM."""

    content: str
    model: str
    used_fallback: bool = False


class ActivityUnit(StrEnum):
    """Unite physique d'une donnee d'activite extraite d'un document."""

    KWH = "kWh"
    MWH = "MWh"
    LITRE = "L"
    M3 = "m3"
    KG = "kg"
    TONNE = "t"
    KM = "km"
    EURO = "EUR"


class EmissionScope(StrEnum):
    """Scope du GHG Protocol auquel rattacher une emission."""

    SCOPE_1 = "scope_1"
    SCOPE_2 = "scope_2"
    SCOPE_3 = "scope_3"


class EsrsDatapoint(StrEnum):
    """Point de donnee ESRS (sous-ensemble climat/energie d'ESRS E1)."""

    E1_5_ENERGY = "E1-5"
    E1_6_GHG = "E1-6"
    UNMAPPED = "unmapped"


class DocumentPage(BaseModel):
    """Page d'un document source, rendue en image pour l'extraction vision."""

    page_number: int = Field(ge=1)
    image_base64: str
    media_type: str = "image/png"


class SourceDocument(BaseModel):
    """Document source uploade (facture, certificat, rapport), decompose en pages."""

    doc_id: str
    title: str
    pages: list[DocumentPage]

    @property
    def page_count(self) -> int:
        return len(self.pages)


class ActivityCategory(StrEnum):
    """Categorie de donnee d'activite, cle de liaison vers un facteur d'emission."""

    ELECTRICITY = "electricity"
    NATURAL_GAS = "natural_gas"
    DISTRICT_HEATING = "district_heating"
    DIESEL = "diesel"
    PETROL = "petrol"
    BUSINESS_TRAVEL_CAR = "business_travel_car"
    WASTE = "waste"


class ExtractedIndicator(BaseModel):
    """Donnee d'activite extraite d'une page, avant calcul carbone."""

    category: ActivityCategory
    value: float = Field(ge=0.0)
    unit: ActivityUnit
    source_page: int = Field(ge=1)
    raw_excerpt: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    datapoint: EsrsDatapoint = EsrsDatapoint.UNMAPPED


class ExtractionResult(BaseModel):
    """Resultat structure de l'extraction multimodale d'un document."""

    doc_id: str
    indicators: list[ExtractedIndicator] = Field(default_factory=list)


class EmissionFactor(BaseModel):
    """Facteur d'emission : kg CO2e par unite d'activite, avec sa source."""

    category: ActivityCategory
    unit: ActivityUnit
    kg_co2e_per_unit: float = Field(ge=0.0)
    scope: EmissionScope
    source: str


class EmissionLine(BaseModel):
    """Ligne du bilan : une activite convertie en CO2e, tracable a sa source."""

    category: ActivityCategory
    activity_value: float
    activity_unit: ActivityUnit
    kg_co2e: float
    scope: EmissionScope
    datapoint: EsrsDatapoint
    source_page: int
    factor_source: str


class FootprintReport(BaseModel):
    """Bilan carbone consolide d'un document, sourcé et auditable."""

    doc_id: str
    reporting_year: int
    lines: list[EmissionLine] = Field(default_factory=list)
    total_kg_co2e: float = 0.0
    by_scope_kg_co2e: dict[EmissionScope, float] = Field(default_factory=dict)
    narrative: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RetrievedPassage(BaseModel):
    """Passage du corpus reglementaire ESRS retrouve pour ancrer une reponse."""

    doc_id: str
    datapoint: EsrsDatapoint
    text: str
    score: float


class ChatAnswer(BaseModel):
    """Reponse a une question reglementaire, avec ses passages sources."""

    answer: str
    passages: list[RetrievedPassage] = Field(default_factory=list)
    used_fallback: bool = False
