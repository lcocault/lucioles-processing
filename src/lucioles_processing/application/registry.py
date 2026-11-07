"""Registre des implémentations (adaptateurs) disponibles pour chaque étape."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ..config import ChainDefinition
from ..domain.ports import (
    DataFetcher,
    DataReader,
    IndicatorCalculator,
    IndicatorRepository,
    ProductBuilder,
    ProductDistributor,
)
from ..domain.run import Step


@dataclass(frozen=True)
class Components:
    """Les six implémentations qui composent une chaîne opérationnelle."""

    fetcher: DataFetcher
    reader: DataReader
    calculator: IndicatorCalculator
    repository: IndicatorRepository
    builder: ProductBuilder
    distributor: ProductDistributor


@dataclass(frozen=True)
class BuildContext:
    """Ce que reçoit une fabrique pour construire son adaptateur."""

    definition: ChainDefinition
    params: Mapping[str, Any]
    step: Step
    use: str

    def require(self, key: str) -> Any:
        """Paramètre obligatoire de l'étape, avec un message d'erreur explicite."""
        if key not in self.params or self.params[key] in (None, ""):
            raise ValueError(f"[étape {self.step.value}, '{self.use}'] paramètre '{key}' manquant")
        return self.params[key]


Factory = Callable[[BuildContext], Any]


class Registry:
    def __init__(self) -> None:
        self._factories: dict[Step, dict[str, Factory]] = {step: {} for step in Step}

    def register(self, step: Step, name: str, factory: Factory) -> None:
        if name in self._factories[step]:
            raise ValueError(f"Implémentation '{name}' déjà enregistrée pour l'étape '{step.value}'")
        self._factories[step][name] = factory

    def names(self, step: Step) -> list[str]:
        return sorted(self._factories[step])

    def validate(self, definition: ChainDefinition) -> None:
        """Vérifie que chaque `use` de la définition est connu."""
        for step, spec in definition.steps.items():
            if spec.use not in self._factories[step]:
                raise ValueError(
                    f"Étape '{step.value}' : implémentation '{spec.use}' inconnue "
                    f"(disponibles : {self.names(step)})"
                )

    def build(self, definition: ChainDefinition) -> Components:
        """Construit les six composants d'une chaîne."""
        self.validate(definition)

        def make(step: Step):
            spec = definition.steps[step]
            return self._factories[step][spec.use](BuildContext(definition, spec.params, step, spec.use))

        return Components(
            fetcher=make(Step.FETCH),
            reader=make(Step.READ),
            calculator=make(Step.CALCULATE),
            repository=make(Step.SAVE),
            builder=make(Step.BUILD),
            distributor=make(Step.DISTRIBUTE),
        )
