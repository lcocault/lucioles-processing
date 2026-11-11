"""Collecte des données sources pour une période donnée.

Chaque source est résolue vers un fichier local : soit un chemin (éventuellement
paramétré par la période), soit une URL téléchargée dans un cache.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..config import SourceConfig
from ..domain.model import FetchedFile, Period
from .download import download

log = logging.getLogger(__name__)


def collect(source: SourceConfig, period: Period, download_dir: Path) -> FetchedFile:
    """Fichier local de la source pour la période.

    Un chemin local est utilisé en place ; une URL est téléchargée dans `download_dir`, ou simplement
    vérifiée si la copie locale est déjà à jour (voir `download`).
    """
    fields = period.fields()

    if source.path:
        path = Path(source.path.format(**fields))
        if not path.exists():
            raise FileNotFoundError(f"[{source.name}] fichier introuvable : {path}")
        return FetchedFile.local(path)

    url = source.url.format(**fields)
    target = download_dir / str(period) / source.name / Path(url.split("?")[0]).name
    return download(url, target)
