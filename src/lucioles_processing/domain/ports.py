"""Ports de la chaîne de traitement : une abstraction par étape, plus l'écoute des exécutions.

Les adaptateurs (paquet `adapters`) implémentent ces ports ; le domaine n'en connaît aucun.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .model import Dataset, IndicatorValue, Period, ProductFile
from .run import ChainRun

#: Données externes récupérées : nom de la source -> fichier local.
RawData = Mapping[str, Path]


@dataclass(frozen=True)
class StepContext:
    """Contexte transmis à chaque étape d'une exécution."""

    run_id: str
    chain: str
    period: Period
    workspace: Path  # espace de travail propre à l'exécution ; créé par l'exécuteur

    def directory(self, *parts: str) -> Path:
        """Sous-dossier de l'espace de travail, créé si nécessaire."""
        path = self.workspace.joinpath(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path


class DataFetcher(ABC):
    """Étape 1 : récupère les données externes dans l'espace de travail."""

    @abstractmethod
    def fetch(self, ctx: StepContext) -> RawData: ...


class DataReader(ABC):
    """Étape 2 : lit les données récupérées et les mappe vers le modèle interne."""

    @abstractmethod
    def read(self, ctx: StepContext, raw: RawData) -> Dataset: ...


class IndicatorCalculator(ABC):
    """Étape 3 : calcule les indicateurs."""

    @abstractmethod
    def calculate(self, ctx: StepContext, dataset: Dataset) -> Sequence[IndicatorValue]: ...


class IndicatorRepository(ABC):
    """Étape 4 : enregistre les indicateurs. L'écriture doit être idempotente par (indicateur, période)."""

    @abstractmethod
    def save(self, ctx: StepContext, values: Sequence[IndicatorValue]) -> None: ...


class ProductBuilder(ABC):
    """Étape 5 : produit les fichiers de diffusion dans l'espace de travail."""

    @abstractmethod
    def build(
        self, ctx: StepContext, dataset: Dataset, values: Sequence[IndicatorValue]
    ) -> Sequence[ProductFile]: ...


class ProductDistributor(ABC):
    """Étape 6 : distribue les fichiers produits vers leur destination."""

    @abstractmethod
    def distribute(self, ctx: StepContext, products: Sequence[ProductFile]) -> None: ...


class RunListener(ABC):
    """Notifié à chaque changement d'état d'une exécution (début, étapes, fin).

    L'objet `ChainRun` transmis doit être traité en lecture seule. Une exception levée par
    un écouteur n'interrompt pas la chaîne.
    """

    @abstractmethod
    def run_updated(self, run: ChainRun) -> None: ...
