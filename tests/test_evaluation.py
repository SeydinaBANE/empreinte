"""Tests du scorer d'evaluation d'extraction."""

from __future__ import annotations

import pytest

from empreinte.evaluation import score_extraction
from empreinte.schemas import ActivityCategory, ActivityUnit, ExtractedIndicatorDraft


def _ind(category: ActivityCategory, value: float) -> ExtractedIndicatorDraft:
    return ExtractedIndicatorDraft(
        category=category, value=value, unit=ActivityUnit.KWH, source_page=1
    )


def test_perfect_match_scores_one() -> None:
    gold = [_ind(ActivityCategory.ELECTRICITY, 1000), _ind(ActivityCategory.DIESEL, 50)]
    report = score_extraction(gold, gold)
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.f1 == 1.0
    assert report.value_accuracy == 1.0


def test_missing_prediction_lowers_recall() -> None:
    gold = [_ind(ActivityCategory.ELECTRICITY, 1000), _ind(ActivityCategory.DIESEL, 50)]
    predicted = [_ind(ActivityCategory.ELECTRICITY, 1000)]
    report = score_extraction(predicted, gold)
    assert report.recall == 0.5
    assert report.precision == 1.0


def test_extra_prediction_lowers_precision() -> None:
    gold = [_ind(ActivityCategory.ELECTRICITY, 1000)]
    predicted = [_ind(ActivityCategory.ELECTRICITY, 1000), _ind(ActivityCategory.WASTE, 10)]
    report = score_extraction(predicted, gold)
    assert report.precision == 0.5
    assert report.recall == 1.0


def test_value_accuracy_uses_tolerance() -> None:
    gold = [_ind(ActivityCategory.ELECTRICITY, 1000)]
    predicted = [_ind(ActivityCategory.ELECTRICITY, 1100)]
    assert score_extraction(predicted, gold, value_tolerance=0.05).value_accuracy == 0.0
    assert score_extraction(predicted, gold, value_tolerance=0.2).value_accuracy == 1.0


def test_empty_inputs_score_one() -> None:
    report = score_extraction([], [])
    assert report.f1 == 1.0
    assert report.value_accuracy == 1.0


def test_per_category_breakdown() -> None:
    gold = [_ind(ActivityCategory.ELECTRICITY, 1000)]
    predicted = [_ind(ActivityCategory.WASTE, 10)]
    report = score_extraction(predicted, gold)
    categories = {score.category for score in report.per_category}
    assert categories == {"electricity", "waste"}
    assert report.f1 == pytest.approx(0.0)
