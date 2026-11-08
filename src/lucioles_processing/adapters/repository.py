"""Étape 4 : enregistrement des indicateurs (implémentations simples ; PostgreSQL : épopée E2)."""

from __future__ import annotations

from collections.abc import Sequence

from ..domain.model import IndicatorValue, Period, Territory
from ..domain.ports import IndicatorRepository, StepContext


class NullRepository(IndicatorRepository):
    """N'enregistre rien."""

    def save(
        self, ctx: StepContext, territories: Sequence[Territory], values: Sequence[IndicatorValue]
    ) -> None:
        return None


class InMemoryRepository(IndicatorRepository):
    """Garde les valeurs en mémoire ; idempotent par (indicateur, période). Pour les tests."""

    def __init__(self) -> None:
        self.store: dict[tuple[str, Period], list[IndicatorValue]] = {}

    def save(
        self, ctx: StepContext, territories: Sequence[Territory], values: Sequence[IndicatorValue]
    ) -> None:
        for key in {(v.indicator, v.period) for v in values}:
            self.store[key] = [v for v in values if (v.indicator, v.period) == key]
