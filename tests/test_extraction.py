"""Tests de l'extraction multimodale et du parsing JSON defensif."""

from __future__ import annotations

import pytest

from empreinte.extraction import ExtractionError, Extractor
from empreinte.schemas import ActivityCategory, EsrsDatapoint, SourceDocument
from tests.conftest import make_gateway

_VALID = (
    '[{"category": "electricity", "value": 1000, "unit": "kWh", "source_page": 1},'
    ' {"category": "diesel", "value": 50, "unit": "L", "source_page": 2}]'
)


async def test_extract_returns_mapped_indicators(demo_document: SourceDocument) -> None:
    extractor = Extractor(make_gateway(_VALID))
    result = await extractor.extract(demo_document)
    assert len(result.indicators) == 2
    assert result.indicators[0].category is ActivityCategory.ELECTRICITY
    assert result.indicators[0].datapoint is EsrsDatapoint.E1_5_ENERGY


async def test_extract_tolerates_markdown_fences(demo_document: SourceDocument) -> None:
    fenced = "Voici le resultat:\n```json\n" + _VALID + "\n```"
    extractor = Extractor(make_gateway(fenced))
    result = await extractor.extract(demo_document)
    assert len(result.indicators) == 2


async def test_extract_skips_invalid_items(demo_document: SourceDocument) -> None:
    mixed = (
        '[{"category": "electricity", "value": 1, "unit": "kWh", "source_page": 1},'
        ' {"category": "unknown", "value": 1, "unit": "kWh", "source_page": 1}]'
    )
    extractor = Extractor(make_gateway(mixed))
    result = await extractor.extract(demo_document)
    assert len(result.indicators) == 1


async def test_extract_raises_on_invalid_json(demo_document: SourceDocument) -> None:
    extractor = Extractor(make_gateway("[pas du json]"))
    with pytest.raises(ExtractionError):
        await extractor.extract(demo_document)


async def test_extract_raises_without_array(demo_document: SourceDocument) -> None:
    extractor = Extractor(make_gateway("aucun tableau ici"))
    with pytest.raises(ExtractionError):
        await extractor.extract(demo_document)


async def test_low_confidence_is_flagged_for_review(demo_document: SourceDocument) -> None:
    payload = '[{"category": "electricity", "value": 1, "unit": "kWh", "source_page": 1, "confidence": 0.2}]'
    extractor = Extractor(make_gateway(payload), min_confidence=0.5)
    result = await extractor.extract(demo_document)
    assert result.indicators[0].needs_review is True


async def test_high_confidence_not_flagged(demo_document: SourceDocument) -> None:
    payload = '[{"category": "electricity", "value": 1, "unit": "kWh", "source_page": 1, "confidence": 0.9}]'
    extractor = Extractor(make_gateway(payload), min_confidence=0.5)
    result = await extractor.extract(demo_document)
    assert result.indicators[0].needs_review is False


def test_extraction_schema_is_array() -> None:
    from empreinte.extraction import extraction_schema

    schema = extraction_schema()
    assert schema["type"] == "array"
    assert "items" in schema
