"""Moteur carbone deterministe : convertit des donnees d'activite en kg CO2e.

Le LLM extrait les donnees d'activite ; ce moteur seul calcule les emissions, a partir
d'un catalogue de facteurs d'emission source (type Base Carbone ADEME). Le calcul est
pur et reproductible : aucune estimation n'est confiee au modele.
"""

from __future__ import annotations

from empreinte.observability import METRICS, record_span
from empreinte.schemas import (
    ActivityCategory,
    ActivityUnit,
    EmissionFactor,
    EmissionLine,
    EmissionScope,
    ExtractedIndicator,
)
from empreinte.taxonomy import datapoint_for

_FACTOR_SOURCE = "ADEME Base Carbone v23.1"

_DEFAULT_FACTORS: tuple[EmissionFactor, ...] = (
    EmissionFactor(
        category=ActivityCategory.ELECTRICITY,
        unit=ActivityUnit.KWH,
        kg_co2e_per_unit=0.0599,
        scope=EmissionScope.SCOPE_2,
        source=_FACTOR_SOURCE,
    ),
    EmissionFactor(
        category=ActivityCategory.NATURAL_GAS,
        unit=ActivityUnit.KWH,
        kg_co2e_per_unit=0.227,
        scope=EmissionScope.SCOPE_1,
        source=_FACTOR_SOURCE,
    ),
    EmissionFactor(
        category=ActivityCategory.DISTRICT_HEATING,
        unit=ActivityUnit.KWH,
        kg_co2e_per_unit=0.116,
        scope=EmissionScope.SCOPE_2,
        source=_FACTOR_SOURCE,
    ),
    EmissionFactor(
        category=ActivityCategory.DIESEL,
        unit=ActivityUnit.LITRE,
        kg_co2e_per_unit=2.51,
        scope=EmissionScope.SCOPE_1,
        source=_FACTOR_SOURCE,
    ),
    EmissionFactor(
        category=ActivityCategory.PETROL,
        unit=ActivityUnit.LITRE,
        kg_co2e_per_unit=2.28,
        scope=EmissionScope.SCOPE_1,
        source=_FACTOR_SOURCE,
    ),
    EmissionFactor(
        category=ActivityCategory.BUSINESS_TRAVEL_CAR,
        unit=ActivityUnit.KM,
        kg_co2e_per_unit=0.193,
        scope=EmissionScope.SCOPE_3,
        source=_FACTOR_SOURCE,
    ),
    EmissionFactor(
        category=ActivityCategory.WASTE,
        unit=ActivityUnit.KG,
        kg_co2e_per_unit=0.467,
        scope=EmissionScope.SCOPE_3,
        source=_FACTOR_SOURCE,
    ),
)

_UNIT_CONVERSIONS: dict[tuple[ActivityUnit, ActivityUnit], float] = {
    (ActivityUnit.MWH, ActivityUnit.KWH): 1000.0,
    (ActivityUnit.TONNE, ActivityUnit.KG): 1000.0,
}


class CarbonComputationError(ValueError):
    """Donnee d'activite incompatible avec le catalogue de facteurs."""


class EmissionFactorCatalog:
    """Catalogue indexe par categorie d'activite."""

    def __init__(self, factors: tuple[EmissionFactor, ...] = _DEFAULT_FACTORS) -> None:
        self._by_category: dict[ActivityCategory, EmissionFactor] = {f.category: f for f in factors}

    def factor_for(self, category: ActivityCategory) -> EmissionFactor:
        """Retourne le facteur d'emission d'une categorie ou leve une erreur si absent."""
        factor = self._by_category.get(category)
        if factor is None:
            raise CarbonComputationError(f"aucun facteur d'emission pour {category}")
        return factor


def _convert(value: float, from_unit: ActivityUnit, to_unit: ActivityUnit) -> float:
    """Convertit une valeur d'activite vers l'unite canonique du facteur."""
    if from_unit == to_unit:
        return value
    ratio = _UNIT_CONVERSIONS.get((from_unit, to_unit))
    if ratio is None:
        raise CarbonComputationError(f"conversion impossible de {from_unit} vers {to_unit}")
    return value * ratio


class CarbonEngine:
    """Convertit des indicateurs d'activite en lignes d'emission CO2e."""

    def __init__(self, catalog: EmissionFactorCatalog | None = None) -> None:
        self._catalog = catalog or EmissionFactorCatalog()

    def compute_line(self, indicator: ExtractedIndicator) -> EmissionLine:
        """Calcule la ligne d'emission d'un indicateur d'activite."""
        factor = self._catalog.factor_for(indicator.category)
        canonical_value = _convert(indicator.value, indicator.unit, factor.unit)
        kg_co2e = round(canonical_value * factor.kg_co2e_per_unit, 3)
        return EmissionLine(
            category=indicator.category,
            activity_value=indicator.value,
            activity_unit=indicator.unit,
            kg_co2e=kg_co2e,
            scope=factor.scope,
            datapoint=datapoint_for(indicator.category),
            source_page=indicator.source_page,
            factor_source=factor.source,
        )

    def compute(self, indicators: list[ExtractedIndicator]) -> list[EmissionLine]:
        """Calcule toutes les lignes d'emission d'une liste d'indicateurs."""
        with record_span("carbon.compute", count=str(len(indicators))):
            lines = [self.compute_line(indicator) for indicator in indicators]
        METRICS.incr("carbon.lines", len(lines))
        return lines


def aggregate_by_scope(lines: list[EmissionLine]) -> dict[EmissionScope, float]:
    """Agrege les emissions par scope GHG Protocol."""
    totals: dict[EmissionScope, float] = {}
    for line in lines:
        totals[line.scope] = round(totals.get(line.scope, 0.0) + line.kg_co2e, 3)
    return totals
