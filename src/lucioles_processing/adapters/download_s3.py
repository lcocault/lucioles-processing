"""Téléchargement depuis un bucket S3 (`s3://bucket/clé`), avec les mêmes garanties que le téléchargement HTTP.

Une requête `HEAD` compare l'ETag à celui de la copie locale : le fichier n'est lu que s'il a changé.
Les identifiants viennent de l'environnement AWS standard (jamais du YAML).
"""

from __future__ import annotations

import logging
from datetime import timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlparse

from ..domain.model import FetchedFile
from . import download as http
from .s3 import make_client

log = logging.getLogger(__name__)


def parse_s3_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    key = parsed.path.lstrip("/")
    if parsed.scheme != "s3" or not parsed.netloc or not key or key.endswith("/"):
        raise ValueError(f"URL S3 invalide '{url}' (attendu : s3://bucket/chemin/fichier)")
    return parsed.netloc, key


class _Body:
    """Adapte la réponse S3 à l'interface de `download._store` (méthode `read` et en-têtes)."""

    def __init__(self, response: dict):
        self._stream = response["Body"]
        modified = response.get("LastModified")
        self.headers = {
            "ETag": response.get("ETag"),
            "Last-Modified": format_datetime(modified.astimezone(timezone.utc), usegmt=True) if modified else None,
            "Content-Length": str(response["ContentLength"]) if "ContentLength" in response else None,
        }

    def read(self, size: int) -> bytes:
        return self._stream.read(size)


def download_s3(url: str, target: Path, refresh: str = "if_changed", client=None) -> FetchedFile:
    """Garantit que `target` contient la dernière version de l'objet S3 `url` (voir `download.download`)."""
    from botocore.exceptions import BotoCoreError, ClientError

    if refresh not in http.REFRESH_MODES:
        raise ValueError(f"refresh '{refresh}' inconnu (attendu : {list(http.REFRESH_MODES)})")
    bucket, key = parse_s3_url(url)
    meta = http._read_meta(target) if target.exists() else None
    if meta and refresh == "never":
        return http._result(url, target, meta, "cached")

    client = client or make_client()
    try:
        head = client.head_object(Bucket=bucket, Key=key)
        if meta and meta.get("etag") and meta["etag"] == head.get("ETag"):
            meta["checked_at"] = http._now()
            http._write_meta(target, meta)
            log.info("%s : déjà à jour", target.name)
            return http._result(url, target, meta, "unchanged")
        response = client.get_object(Bucket=bucket, Key=key)
        return http._store(url, target, _Body(response), meta)
    except ClientError as exc:
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        if status >= 500 and meta:
            return http._unverified(url, target, meta, exc)
        raise OSError(f"{url} : objet S3 introuvable ou inaccessible (HTTP {status} : {exc})") from exc
    except BotoCoreError as exc:  # réseau, identifiants absents...
        if meta:
            return http._unverified(url, target, meta, exc)
        raise OSError(f"{url} : accès S3 impossible ({exc})") from exc
