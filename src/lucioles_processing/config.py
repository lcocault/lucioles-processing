"""Définition déclarative d'une chaîne de traitement (fichier YAML).

Exemple : voir `configs/air_quality.example.yaml`. Une chaîne décrit l'indicateur calculé,
ses sources, et l'implémentation (`use`) retenue pour chacune des six étapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .domain.run import Step

METHODS = {"zonal_mean", "nearest_station"}

#: Étapes sans implémentation obligatoire : `none` (ne rien faire) par défaut.
OPTIONAL_STEPS = {Step.SAVE: "none", Step.DISTRIBUTE: "none"}


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


@dataclass(frozen=True)
class StepSpec:
    """Implémentation retenue pour une étape (`use`) et ses paramètres."""

    use: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChainDefinition:
    name: str
    indicator: IndicatorSpec
    sources: dict[str, SourceConfig]
    steps: dict[Step, StepSpec]

    def __post_init__(self) -> None:
        unknown = set(self.indicator.weights) - set(self.sources)
        if unknown:
            raise ValueError(f"Poids définis pour des sources inconnues : {sorted(unknown)}")
        missing = [s.value for s in Step if s not in self.steps]
        if missing:
            raise ValueError(f"Étapes non définies : {missing}")


def parse_chain_definition(raw: dict[str, Any]) -> ChainDefinition:
    """Construit et valide une définition à partir du contenu YAML déjà chargé."""
    if not isinstance(raw, dict):
        raise ValueError("La définition de chaîne doit être un dictionnaire YAML")  # noqa: TRY004 - erreur de configuration, traitée comme les autres
    for key in ("chain", "indicator", "sources", "steps"):
        if key not in raw:
            raise ValueError(f"Clé obligatoire absente : '{key}'")

    valid = {s.value for s in Step}
    unknown = set(raw["steps"]) - valid
    if unknown:
        raise ValueError(f"Étapes inconnues : {sorted(unknown)} (attendu : {sorted(valid)})")

    steps: dict[Step, StepSpec] = {}
    for step in Step:
        cfg = raw["steps"].get(step.value)
        if cfg is None:
            if step not in OPTIONAL_STEPS:
                raise ValueError(f"Étape obligatoire absente : '{step.value}'")
            cfg = {"use": OPTIONAL_STEPS[step]}
        if "use" not in cfg:
            raise ValueError(f"Étape '{step.value}' : 'use' est obligatoire")
        steps[step] = StepSpec(use=cfg["use"], params=dict(cfg.get("params") or {}))

    return ChainDefinition(
        name=str(raw["chain"]),
        indicator=IndicatorSpec(**raw["indicator"]),
        sources={n: SourceConfig(name=n, **c) for n, c in raw["sources"].items()},
        steps=steps,
    )


def load_chain_definition(path: str | Path) -> ChainDefinition:
    return parse_chain_definition(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
