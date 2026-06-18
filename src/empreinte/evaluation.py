"""Evaluation de la qualite d'extraction : precision/rappel/F1 + exactitude numerique.

Detection (P/R/F1) mesuree par categorie d'activite ; l'exactitude numerique compare les
valeurs des paires appariees avec une tolerance relative. Fonctions pures, testables.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from empreinte.schemas import ActivityCategory


class ScoredIndicator(Protocol):
    """Indicateur portant au minimum une categorie et une valeur."""

    category: ActivityCategory
    value: float


@dataclass(frozen=True)
class CategoryScore:
    """Scores de detection pour une categorie."""

    category: str
    true_positives: int
    false_positives: int
    false_negatives: int


@dataclass(frozen=True)
class EvalReport:
    """Rapport d'evaluation agrege."""

    precision: float
    recall: float
    f1: float
    value_accuracy: float
    per_category: list[CategoryScore]


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0.0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _value_accuracy(
    predicted: Sequence[ScoredIndicator],
    expected: Sequence[ScoredIndicator],
    tolerance: float,
) -> float:
    matched = 0
    total = 0
    for category in {item.category for item in expected}:
        preds = [item.value for item in predicted if item.category == category]
        golds = [item.value for item in expected if item.category == category]
        for gold, pred in zip(sorted(golds), sorted(preds), strict=False):
            total += 1
            if gold == 0.0:
                matched += int(pred == 0.0)
            elif abs(pred - gold) / abs(gold) <= tolerance:
                matched += 1
    return matched / total if total else 1.0


def score_extraction(
    predicted: Sequence[ScoredIndicator],
    expected: Sequence[ScoredIndicator],
    value_tolerance: float = 0.05,
) -> EvalReport:
    """Compare indicateurs predits et attendus ; retourne P/R/F1 et l'exactitude numerique."""
    pred_counts = Counter(item.category for item in predicted)
    gold_counts = Counter(item.category for item in expected)

    per_category: list[CategoryScore] = []
    total_tp = total_fp = total_fn = 0
    for category in set(pred_counts) | set(gold_counts):
        predicted_n = pred_counts.get(category, 0)
        expected_n = gold_counts.get(category, 0)
        tp = min(predicted_n, expected_n)
        fp = predicted_n - tp
        fn = expected_n - tp
        total_tp += tp
        total_fp += fp
        total_fn += fn
        per_category.append(
            CategoryScore(
                category=category.value,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
            )
        )

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 1.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 1.0
    return EvalReport(
        precision=round(precision, 3),
        recall=round(recall, 3),
        f1=round(_f1(precision, recall), 3),
        value_accuracy=round(_value_accuracy(predicted, expected, value_tolerance), 3),
        per_category=sorted(per_category, key=lambda score: score.category),
    )
