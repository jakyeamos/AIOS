from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


def precision(predicted: set[str], actual: set[str]) -> float:
    if not predicted:
        return 0.0
    return len(predicted & actual) / len(predicted)


def recall(predicted: set[str], actual: set[str]) -> float:
    if not actual:
        return 1.0
    return len(predicted & actual) / len(actual)


def f1_score(predicted: set[str], actual: set[str]) -> float:
    p = precision(predicted, actual)
    r = recall(predicted, actual)
    if (p + r) == 0:
        return 0.0
    return 2 * (p * r) / (p + r)


@dataclass(slots=True)
class ScoreBundle:
    precision: float
    recall: float
    f1: float
    task_success: bool


def score_set(predicted_items: Iterable[str], actual_items: Iterable[str]) -> ScoreBundle:
    predicted = set(predicted_items)
    actual = set(actual_items)
    p = precision(predicted, actual)
    r = recall(predicted, actual)
    f1 = f1_score(predicted, actual)
    return ScoreBundle(precision=p, recall=r, f1=f1, task_success=bool(predicted & actual))
