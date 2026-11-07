"""Collecte des données sources pour une période donnée.

Chaque source est résolue vers un fichier local : soit un chemin (éventuellement
paramétré par la période), soit une URL téléchargée dans un cache.
"""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

from .config import SourceConfig

log = logging.getLogger(__name__)


def period_fields(period: str) -> dict[str, str]:
    """'2026-10' -> {'period': '2026-10', 'year': '2026', 'month': '10'}"""
    try:
        year, month = period.split("-")
        if not (len(year) == 4 and 1 <= int(month) <= 12):
            raise ValueError
    except ValueError:
        raise ValueError(f"Période invalide '{period}' (format attendu : AAAA-MM)") from None
    return {"period": period, "year": year, "month": month}


def collect(source: SourceConfig, period: str, cache_dir: Path) -> Path:
    """Retourne le chemin local du fichier de la source pour la période."""
    fields = period_fields(period)

    if source.path:
        path = Path(source.path.format(**fields))
        if not path.exists():
            raise FileNotFoundError(f"[{source.name}] fichier introuvable : {path}")
        return path

    url = source.url.format(**fields)
    target = cache_dir / period / source.name / Path(url.split("?")[0]).name
    if target.exists():
        log.info("[%s] déjà en cache : %s", source.name, target)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    log.info("[%s] téléchargement : %s", source.name, url)
    tmp = target.with_suffix(target.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(target)
    return target
