"""Téléchargement avec revalidation : on ne retélécharge un fichier que s'il a changé sur le serveur.

Chaque fichier téléchargé est accompagné d'un fichier `<nom>.meta.json` (ETag, Last-Modified, SHA-256).
À l'exécution suivante, une requête conditionnelle (`If-None-Match` / `If-Modified-Since`) vérifie que la
copie locale est toujours la dernière version.
"""

from __future__ import annotations

import hashlib
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from ..domain.model import FetchedFile

log = logging.getLogger(__name__)

REFRESH_MODES = ("if_changed", "never")
_CHUNK = 1 << 20


def _meta_path(target: Path) -> Path:
    return target.with_name(target.name + ".meta.json")


def _read_meta(target: Path) -> dict | None:
    try:
        return json.loads(_meta_path(target).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_meta(target: Path, meta: dict) -> None:
    _meta_path(target).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _version(meta: dict) -> str | None:
    return meta.get("etag") or meta.get("last_modified") or (meta.get("sha256") or "")[:16] or None


def _result(url: str, target: Path, meta: dict, status: str) -> FetchedFile:
    return FetchedFile(path=target, origin=url, status=status, version=_version(meta), sha256=meta.get("sha256"))


def download(url: str, target: Path, refresh: str = "if_changed", timeout: float = 60) -> FetchedFile:
    """Garantit que `target` contient la dernière version de `url`.

    - `refresh="never"` : une copie déjà présente est utilisée sans interroger le serveur.
    - `refresh="if_changed"` : requête conditionnelle ; 304 -> inchangé ; 200 -> remplacé de façon atomique.
    - Serveur injoignable (ou erreur 5xx) avec une copie locale : on l'utilise, statut `unverified`.
      Sans copie locale, l'erreur est propagée. Les erreurs 4xx sont toujours propagées.
    """
    if refresh not in REFRESH_MODES:
        raise ValueError(f"refresh '{refresh}' inconnu (attendu : {list(REFRESH_MODES)})")
    meta = _read_meta(target) if target.exists() else None

    if meta and refresh == "never":
        return _result(url, target, meta, "cached")

    headers = {"User-Agent": "lucioles-processing"}
    if meta:
        if meta.get("etag"):
            headers["If-None-Match"] = meta["etag"]
        if meta.get("last_modified"):
            headers["If-Modified-Since"] = meta["last_modified"]

    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as resp:
            return _store(url, target, resp, meta)
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and meta:
            meta["checked_at"] = _now()
            _write_meta(target, meta)
            log.info("%s : déjà à jour", target.name)
            return _result(url, target, meta, "unchanged")
        if exc.code >= 500 and meta:
            return _unverified(url, target, meta, exc)
        raise
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        if meta:
            return _unverified(url, target, meta, exc)
        raise


def _unverified(url: str, target: Path, meta: dict, exc: Exception) -> FetchedFile:
    log.warning("%s : version non vérifiable (%s), copie locale utilisée", url, exc)
    return _result(url, target, meta, "unverified")


def _store(url: str, target: Path, resp, previous: dict | None) -> FetchedFile:
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    digest, size = hashlib.sha256(), 0
    try:
        with part.open("wb") as out:
            while chunk := resp.read(_CHUNK):
                out.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        expected = resp.headers.get("Content-Length")
        if expected is not None and int(expected) != size:
            raise OSError(f"Téléchargement tronqué : {size} octets reçus sur {expected} ({url})")
        sha256 = digest.hexdigest()
        meta = {
            "url": url,
            "etag": resp.headers.get("ETag"),
            "last_modified": resp.headers.get("Last-Modified"),
            "sha256": sha256,
            "size": size,
            "downloaded_at": _now(),
            "checked_at": _now(),
        }
        part.replace(target)  # remplacement atomique : jamais de fichier à moitié écrit
        _write_meta(target, meta)
    finally:
        part.unlink(missing_ok=True)
    unchanged = previous is not None and previous.get("sha256") == sha256
    log.info("%s : %s", target.name, "contenu identique" if unchanged else f"téléchargé ({size} octets)")
    return _result(url, target, meta, "unchanged" if unchanged else "downloaded")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
