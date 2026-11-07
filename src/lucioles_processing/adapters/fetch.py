"""Étape 1 : récupération des données externes."""

from __future__ import annotations

from pathlib import Path

from ..config import SourceConfig
from ..domain.ports import DataFetcher, RawData, StepContext
from .collect import collect


class ConfiguredSourcesFetcher(DataFetcher):
    """Résout chaque source de la définition vers un fichier local.

    Un chemin local est utilisé en place ; une URL est téléchargée dans `cache_dir` si ce
    paramètre est fourni (réutilisé d'une exécution à l'autre), sinon dans l'espace de travail.
    """

    def __init__(self, sources: dict[str, SourceConfig], cache_dir: Path | None = None):
        self.sources = sources
        self.cache_dir = cache_dir

    def fetch(self, ctx: StepContext) -> RawData:
        download_dir = self.cache_dir or ctx.directory("raw")
        return {
            name: collect(source, ctx.period, download_dir) for name, source in self.sources.items()
        }
