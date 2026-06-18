"""Tests du mapping taxonomie ESRS."""

from __future__ import annotations

from empreinte.schemas import ActivityCategory, ActivityUnit, EsrsDatapoint, ExtractedIndicator
from empreinte.taxonomy import datapoint_for, label_of, map_indicator


def test_energy_category_maps_to_e1_5() -> None:
    assert datapoint_for(ActivityCategory.ELECTRICITY) is EsrsDatapoint.E1_5_ENERGY


def test_travel_category_maps_to_e1_6() -> None:
    assert datapoint_for(ActivityCategory.BUSINESS_TRAVEL_CAR) is EsrsDatapoint.E1_6_GHG


def test_map_indicator_sets_datapoint() -> None:
    indicator = ExtractedIndicator(
        category=ActivityCategory.WASTE, value=10, unit=ActivityUnit.KG, source_page=1
    )
    assert map_indicator(indicator).datapoint is EsrsDatapoint.E1_6_GHG


def test_label_of_known_datapoint() -> None:
    assert "ESRS E1-5" in label_of(EsrsDatapoint.E1_5_ENERGY)
