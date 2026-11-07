"""Modèle de données interne, indépendant des formats sources et de diffusion."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

LEVELS = range(5)  # niveaux OPF : 0 (meilleur) à 4 (pire)


@dataclass(frozen=True, order=True)
class Period:
    """Période mensuelle, notée `AAAA-MM`."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if not (1 <= self.year <= 9999 and 1 <= self.month <= 12):
            raise ValueError(f"Période invalide {self.year}-{self.month} (format attendu : AAAA-MM)")

    @classmethod
    def parse(cls, text: str) -> Period:
        match = re.fullmatch(r"(\d{4})-(\d{2})", text.strip())
        if not match:
            raise ValueError(f"Période invalide '{text}' (format attendu : AAAA-MM)")
        return cls(int(match[1]), int(match[2]))

    def fields(self) -> dict[str, str]:
        """Champs de substitution des chemins et URLs : `{period}`, `{year}`, `{month}`."""
        return {"period": str(self), "year": f"{self.year:04d}", "month": f"{self.month:02d}"}

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


@dataclass(frozen=True)
class Territory:
    """Un territoire (commune) et sa géométrie en WKT, coordonnées lon/lat (EPSG:4326)."""

    code: str
    name: str = ""
    department: str = ""
    geometry_wkt: str | None = None

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("Le code d'un territoire ne peut pas être vide")


@dataclass(frozen=True)
class Observation:
    """Valeur d'une source de données agrégée sur un territoire (`None` = donnée absente)."""

    source: str
    territory_code: str
    value: float | None


@dataclass(frozen=True)
class Dataset:
    """Données d'entrée d'un calcul : territoires et observations par source, pour une période."""

    period: Period
    territories: tuple[Territory, ...]
    sources: tuple[str, ...]
    observations: tuple[Observation, ...]

    def __post_init__(self) -> None:
        codes = [t.code for t in self.territories]
        if len(set(codes)) != len(codes):
            raise ValueError("Codes de territoires en double")
        known = set(codes)
        for obs in self.observations:
            if obs.territory_code not in known:
                raise ValueError(f"Observation sur un territoire inconnu : {obs.territory_code}")
            if obs.source not in self.sources:
                raise ValueError(f"Observation d'une source inconnue : {obs.source}")

    def value(self, source: str, territory_code: str) -> float | None:
        """Valeur d'une source sur un territoire ; `None` si absente."""
        return self._index().get((source, territory_code))

    def _index(self) -> dict[tuple[str, str], float | None]:
        # Dataset est immuable : l'index est calculé une fois, puis conservé.
        cached = self.__dict__.get("_cache")
        if cached is None:
            cached = {(o.source, o.territory_code): o.value for o in self.observations}
            object.__setattr__(self, "_cache", cached)
        return cached


@dataclass(frozen=True)
class IndicatorValue:
    """Valeur d'un indicateur sur un territoire et une période, avec son niveau OPF."""

    indicator: str
    period: Period
    territory_code: str
    value: float | None
    level: int | None

    def __post_init__(self) -> None:
        if self.level is not None and self.level not in LEVELS:
            raise ValueError(f"Niveau {self.level} invalide (attendu : 0 à 4 ou absent)")
        if self.value is None and self.level is not None:
            raise ValueError("Un niveau ne peut pas exister sans valeur")
        if self.value is not None and self.level is None:
            raise ValueError("Une valeur doit avoir un niveau")


@dataclass(frozen=True)
class ProductFile:
    """Fichier de diffusion produit par une chaîne (KML, GeoJSON, ...)."""

    name: str
    path: Path
    format: str = field(default="")
