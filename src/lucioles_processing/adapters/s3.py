"""Étape 6 : distribution vers un bucket Amazon S3 (ou compatible S3)."""

from __future__ import annotations

import json
import logging
import mimetypes
from collections.abc import Sequence
from datetime import datetime, timezone

from ..domain.model import Period, ProductFile
from ..domain.ports import ProductDistributor, StepContext

log = logging.getLogger(__name__)

CONTENT_TYPES = {
    "kml": "application/vnd.google-earth.kml+xml",
    "geojson": "application/geo+json",
    "gpkg": "application/geopackage+sqlite3",
    "json": "application/json",
    "pmtiles": "application/octet-stream",
}


def make_client(region: str | None = None, endpoint_url: str | None = None):
    """Client boto3 ; les identifiants viennent de l'environnement AWS standard (jamais du YAML)."""
    try:
        import boto3
    except ImportError as exc:
        raise ValueError(
            "L'étape 'distribute: s3' nécessite boto3 : pip install 'lucioles-processing[s3]'"
        ) from exc
    return boto3.client("s3", region_name=region, endpoint_url=endpoint_url)


class S3Distributor(ProductDistributor):
    """Publie dans `s3://<bucket>/<préfixe>/<chaîne>/<période>/` et tient `latest.json` à jour.

    Les fichiers sont réécrits à chaque exécution (idempotent). `latest.json`, dans
    `<préfixe>/<chaîne>/`, pointe sur la période la plus récente : rejouer une période plus ancienne
    ne le fait pas régresser.
    """

    def __init__(self, bucket: str, prefix: str = "", client=None, region: str | None = None,
                 endpoint_url: str | None = None):
        if not bucket:
            raise ValueError("Le nom du bucket S3 est obligatoire")
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self._client = client
        self._region, self._endpoint_url = region, endpoint_url

    @property
    def client(self):
        if self._client is None:
            self._client = make_client(self._region, self._endpoint_url)
        return self._client

    def _key(self, *parts: str) -> str:
        return "/".join(p for p in (self.prefix, *parts) if p)

    def distribute(self, ctx: StepContext, products: Sequence[ProductFile]) -> None:
        files = []
        for product in products:
            key = self._key(ctx.chain, str(ctx.period), product.path.name)
            content_type = (
                CONTENT_TYPES.get(product.format)
                or mimetypes.guess_type(product.path.name)[0]
                or "application/octet-stream"
            )
            self.client.upload_file(
                str(product.path), self.bucket, key, ExtraArgs={"ContentType": content_type}
            )
            files.append({"name": product.path.name, "key": key, "size": product.path.stat().st_size})
            log.info("s3://%s/%s", self.bucket, key)
        self._update_latest(ctx, files)

    def _update_latest(self, ctx: StepContext, files: list[dict]) -> None:
        key = self._key(ctx.chain, "latest.json")
        current = self._read_latest(key)
        if current is not None and current > ctx.period:
            log.info("latest.json conservé (période publiée plus récente : %s)", current)
            return
        body = {
            "chain": ctx.chain,
            "period": str(ctx.period),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "files": files,
        }
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=json.dumps(body, indent=2).encode(),
            ContentType="application/json",
        )

    def _read_latest(self, key: str) -> Period | None:
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
        except self.client.exceptions.NoSuchKey:
            return None
        return Period.parse(json.loads(obj["Body"].read())["period"])
