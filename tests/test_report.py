"""Tests de la construction du bilan carbone."""

from __future__ import annotations

import pytest

from empreinte.factors import CarbonEngine
from empreinte.report import ReportBuilder
from empreinte.schemas import EmissionScope, ExtractedIndicator, ExtractionResult
from tests.conftest import make_gateway


def _extraction(indicators: list[ExtractedIndicator]) -> ExtractionResult:
    return ExtractionResult(doc_id="doc-test", indicators=indicators)


async def test_build_uses_llm_narrative(indicators: list[ExtractedIndicator]) -> None:
    builder = ReportBuilder(CarbonEngine(), make_gateway("Synthese redigee."), 2025)
    report = await builder.build(_extraction(indicators))
    assert report.narrative == "Synthese redigee."
    assert report.reporting_year == 2025


async def test_build_totals_match_engine(indicators: list[ExtractedIndicator]) -> None:
    builder = ReportBuilder(CarbonEngine(), make_gateway("ok"), 2025)
    report = await builder.build(_extraction(indicators))
    expected = round(sum(line.kg_co2e for line in report.lines), 3)
    assert report.total_kg_co2e == pytest.approx(expected)
    assert EmissionScope.SCOPE_2 in report.by_scope_kg_co2e


async def test_build_falls_back_to_facts_when_llm_silent(
    indicators: list[ExtractedIndicator],
) -> None:
    builder = ReportBuilder(CarbonEngine(), make_gateway(""), 2025)
    report = await builder.build(_extraction(indicators))
    assert "Bilan 2025" in report.narrative
