"""Tests du moteur carbone deterministe."""

from __future__ import annotations

import pytest

from empreinte.factors import (
    CarbonComputationError,
    CarbonEngine,
    EmissionFactorCatalog,
    aggregate_by_scope,
)
from empreinte.schemas import (
    ActivityCategory,
    ActivityUnit,
    EmissionScope,
    ExtractedIndicator,
)


def _indicator(category: ActivityCategory, value: float, unit: ActivityUnit) -> ExtractedIndicator:
    return ExtractedIndicator(category=category, value=value, unit=unit, source_page=1)


def test_compute_line_electricity_scope_2() -> None:
    engine = CarbonEngine()
    line = engine.compute_line(_indicator(ActivityCategory.ELECTRICITY, 1000, ActivityUnit.KWH))
    assert line.scope is EmissionScope.SCOPE_2
    assert line.kg_co2e == pytest.approx(59.9)


def test_compute_line_converts_mwh_to_kwh() -> None:
    engine = CarbonEngine()
    line = engine.compute_line(_indicator(ActivityCategory.ELECTRICITY, 1, ActivityUnit.MWH))
    assert line.kg_co2e == pytest.approx(59.9)


def test_compute_line_unknown_unit_conversion_raises() -> None:
    engine = CarbonEngine()
    with pytest.raises(CarbonComputationError):
        engine.compute_line(_indicator(ActivityCategory.ELECTRICITY, 1, ActivityUnit.LITRE))


def test_catalog_missing_factor_raises() -> None:
    catalog = EmissionFactorCatalog(factors=())
    with pytest.raises(CarbonComputationError):
        catalog.factor_for(ActivityCategory.ELECTRICITY)


def test_aggregate_by_scope_sums_per_scope() -> None:
    engine = CarbonEngine()
    lines = engine.compute(
        [
            _indicator(ActivityCategory.ELECTRICITY, 1000, ActivityUnit.KWH),
            _indicator(ActivityCategory.NATURAL_GAS, 1000, ActivityUnit.KWH),
            _indicator(ActivityCategory.BUSINESS_TRAVEL_CAR, 100, ActivityUnit.KM),
        ]
    )
    totals = aggregate_by_scope(lines)
    assert totals[EmissionScope.SCOPE_1] == pytest.approx(227.0)
    assert totals[EmissionScope.SCOPE_2] == pytest.approx(59.9)
    assert totals[EmissionScope.SCOPE_3] == pytest.approx(19.3)
