"""Étape 3 : calcul des indicateurs."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence

from ..config import IndicatorSpec
from ..domain.model import Dataset, IndicatorValue
from ..domain.ports import IndicatorCalculator, StepContext


class WeightedSumCalculator(IndicatorCalculator):
    """Somme pondérée des sources, puis niveau OPF 0..4 d'après les seuils.

    Une donnée absente (sur une source pondérée) rend l'indicateur absent : jamais traité comme 0.
    Le niveau est le nombre de seuils inférieurs ou égaux à la valeur.
    """

    def __init__(self, spec: IndicatorSpec):
        self.spec = spec

    def calculate(self, ctx: StepContext, dataset: Dataset) -> Sequence[IndicatorValue]:
        result = []
        for territory in dataset.territories:
            parts = [dataset.value(src, territory.code) for src in self.spec.weights]
            if any(p is None for p in parts):
                value, level = None, None
            else:
                value = sum(p * w for p, w in zip(parts, self.spec.weights.values(), strict=True))
                level = bisect_right(self.spec.thresholds, value)
            result.append(IndicatorValue(self.spec.name, dataset.period, territory.code, value, level))
        return result
