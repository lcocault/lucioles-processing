"""Collecte des données sources pour une période donnée.

Chaque source est résolue vers un fichier local : soit un chemin (éventuellement
paramétré par la période), soit une URL téléchargée dans un cache.
"""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

from ..config import SourceConfig
from ..domain.model import Period

log = logging.getLogger(__name__)


def collect(source: SourceConfig, period: Period, download_dir: Path) -> Path:
    """Retourne le chemin local du fichier de la source pour la période.

    Un chemin local est utilisé en place ; une URL est téléchargée dans `download_dir`
    (sauf si le fichier y est déjà).
    """
    fields = period.fields()

    if source.path:
        path = Path(source.path.format(**fields))
        if not path.exists():
            raise FileNotFoundError(f"[{source.name}] fichier introuvable : {path}")
        return path

    url = source.url.format(**fields)
    target = download_dir / str(period) / source.name / Path(url.split("?")[0]).name
    if target.exists():
        log.info("[%s] déjà en cache : %s", source.name, target)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    log.info("[%s] téléchargement : %s", source.name, url)
    tmp = target.with_suffix(target.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(target)
    return target
