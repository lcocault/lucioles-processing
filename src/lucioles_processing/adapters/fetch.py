"""Étape 1 : récupération des données externes (sources de mesure et fond administratif)."""

from __future__ import annotations

from pathlib import Path

from ..config import BoundariesConfig, SourceConfig
from ..domain.model import FetchedFile
from ..domain.ports import BOUNDARIES_KEY, DataFetcher, RawData, StepContext
from .collect import collect
from .download import download


class ConfiguredSourcesFetcher(DataFetcher):
    """Récupère le fond administratif et chaque source de la définition.

    Un chemin local est utilisé en place. Une URL est téléchargée dans `cache_dir` (sinon dans l'espace de
    travail de l'exécution) ; si la copie y est déjà, on vérifie auprès du serveur qu'elle est à jour
    et on ne retélécharge que si elle a changé.
    """

    def __init__(
        self,
        sources: dict[str, SourceConfig],
        boundaries: BoundariesConfig,
        cache_dir: Path | None = None,
    ):
        self.sources = sources
        self.boundaries = boundaries
        self.cache_dir = cache_dir

    def fetch(self, ctx: StepContext) -> RawData:
        download_dir = self.cache_dir or ctx.directory("raw")
        raw = {BOUNDARIES_KEY: self._fetch_boundaries(download_dir)}
        for name, source in self.sources.items():
            raw[name] = collect(source, ctx.period, download_dir)
        return raw

    def _fetch_boundaries(self, download_dir: Path) -> FetchedFile:
        b = self.boundaries
        if b.path:
            path = Path(b.path)
            if not path.exists():
                raise FileNotFoundError(f"[boundaries] fichier introuvable : {path}")
            return FetchedFile.local(path)
        target = download_dir / BOUNDARIES_KEY / Path(b.url.split("?")[0]).name
        return download(b.url, target, refresh=b.refresh)
