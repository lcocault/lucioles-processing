"""Configuration déclarative d'un indicateur (fichier YAML)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

METHODS = {"zonal_mean", "nearest_station"}


@dataclass
class SourceConfig:
    """Une source de données et la manière de l'agréger par commune.

    `path` et `url` peuvent contenir `{period}` (ex. 2026-10), `{year}` et `{month}`.
    """

    name: str
    method: str
    path: str | None = None
    url: str | None = None
    field: str | None = None
    dims: list[str] | None = None
    condition: str | None = None

    def __post_init__(self) -> None:
        if self.method not in METHODS:
            raise ValueError(
                f"[{self.name}] méthode '{self.method}' inconnue (attendu : {sorted(METHODS)})"
            )
        if not (self.path or self.url):
            raise ValueError(f"[{self.name}] 'path' ou 'url' est obligatoire")
        if self.method == "nearest_station" and (not self.field or not self.dims):
            raise ValueError(f"[{self.name}] 'field' et 'dims' sont obligatoires pour nearest_station")


@dataclass
class IndicatorSpec:
    """Calcul de l'indicateur final : somme pondérée des sources, puis classes OPF."""

    name: str
    weights: dict[str, float]
    thresholds: list[float]  # n seuils croissants -> n+1 classes (0..n)

    def __post_init__(self) -> None:
        if self.thresholds != sorted(self.thresholds):
            raise ValueError("Les seuils doivent être croissants")
        if len(self.thresholds) != 4:
            raise ValueError("Les couleurs OPF supposent 4 seuils (5 classes)")


@dataclass
class IndicatorConfig:
    indicator: IndicatorSpec
    sources: dict[str, SourceConfig]
    departments: list[str] = field(default_factory=list)  # vide = tous les départements

    def __post_init__(self) -> None:
        unknown = set(self.indicator.weights) - set(self.sources)
        if unknown:
            raise ValueError(f"Poids définis pour des sources inconnues : {sorted(unknown)}")


def load_config(path: str | Path) -> IndicatorConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    sources = {name: SourceConfig(name=name, **cfg) for name, cfg in raw["sources"].items()}
    return IndicatorConfig(
        indicator=IndicatorSpec(**raw["indicator"]),
        sources=sources,
        departments=[str(d) for d in raw.get("departments", [])],
    )
