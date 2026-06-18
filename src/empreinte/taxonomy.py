"""Taxonomie ESRS : rattache chaque categorie d'activite a un point de donnee ESRS E1.

Les categories d'energie (electricite, gaz, chaleur) relevent de la consommation
energetique ESRS E1-5 ; les combustibles, deplacements et dechets relevent des emissions
de GES ESRS E1-6. Le mapping est explicite et versionnable plutot que decide par le LLM.
"""

from __future__ import annotations

from empreinte.schemas import ActivityCategory, EsrsDatapoint, ExtractedIndicator

_CATEGORY_TO_DATAPOINT: dict[ActivityCategory, EsrsDatapoint] = {
    ActivityCategory.ELECTRICITY: EsrsDatapoint.E1_5_ENERGY,
    ActivityCategory.NATURAL_GAS: EsrsDatapoint.E1_5_ENERGY,
    ActivityCategory.DISTRICT_HEATING: EsrsDatapoint.E1_5_ENERGY,
    ActivityCategory.DIESEL: EsrsDatapoint.E1_6_GHG,
    ActivityCategory.PETROL: EsrsDatapoint.E1_6_GHG,
    ActivityCategory.BUSINESS_TRAVEL_CAR: EsrsDatapoint.E1_6_GHG,
    ActivityCategory.WASTE: EsrsDatapoint.E1_6_GHG,
}

_DATAPOINT_LABELS: dict[EsrsDatapoint, str] = {
    EsrsDatapoint.E1_5_ENERGY: "ESRS E1-5 — Consommation et mix energetiques",
    EsrsDatapoint.E1_6_GHG: "ESRS E1-6 — Emissions brutes de GES (scopes 1, 2, 3)",
    EsrsDatapoint.UNMAPPED: "Non rattache a un point de donnee ESRS",
}


def datapoint_for(category: ActivityCategory) -> EsrsDatapoint:
    """Retourne le point de donnee ESRS rattache a une categorie d'activite."""
    return _CATEGORY_TO_DATAPOINT.get(category, EsrsDatapoint.UNMAPPED)


def label_of(datapoint: EsrsDatapoint) -> str:
    """Retourne le libelle humain d'un point de donnee ESRS."""
    return _DATAPOINT_LABELS[datapoint]


def map_indicator(indicator: ExtractedIndicator) -> ExtractedIndicator:
    """Retourne une copie de l'indicateur avec son point de donnee ESRS renseigne."""
    return indicator.model_copy(update={"datapoint": datapoint_for(indicator.category)})
