"""Chaîne complète publiée dans un bucket S3 (S3 simulé en mémoire par moto : aucun accès AWS réel)."""

import json

import boto3
import pandas as pd
import pytest
from moto import mock_aws

from lucioles_processing.cli import main

pytestmark = pytest.mark.e2e

BUCKET = "lucioles-e2e"

CHAIN = """
chain: air
indicator: {{name: air, weights: {{pm10: 1.0}}, thresholds: [10, 20, 30, 40]}}
boundaries:
  path: {admin}
  departments: ["31"]
sources:
  pm10:
    method: nearest_station
    path: {data}/pm10_{{period}}.csv
    field: pm10
    dims: [lon, lat]
steps:
  fetch: {{use: configured_sources}}
  read: {{use: commune_aggregation}}
  calculate: {{use: weighted_sum}}
  build:
    use: map_files
    params: {{formats: [geojson, kml]}}
  distribute:
    use: s3
    params: {{bucket: {bucket}, prefix: opf, region: eu-west-3}}
"""


@pytest.fixture
def env(communes, tmp_path, monkeypatch):
    for key, value in {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test",
                       "AWS_DEFAULT_REGION": "eu-west-3"}.items():
        monkeypatch.setenv(key, value)
    admin = tmp_path / "admin.gpkg"
    communes.to_file(admin, driver="GPKG")
    pd.DataFrame({"lon": [1.05, 1.25], "lat": [43.05, 43.25], "pm10": [5.0, 45.0]}).to_csv(
        tmp_path / "pm10_2026-10.csv", sep=";", index=False
    )
    cfg = tmp_path / "chain.yaml"
    cfg.write_text(CHAIN.format(admin=admin, data=tmp_path, bucket=BUCKET))
    with mock_aws():
        yield cfg, tmp_path


def run(cfg, tmp_path):
    return main(["run", "--config", str(cfg), "--period", "2026-10", "--workspace", str(tmp_path / "ws")])


def create_bucket():
    s3 = boto3.client("s3", region_name="eu-west-3")
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
    return s3


def test_chain_publishes_to_s3(env):
    cfg, tmp_path = env
    s3 = create_bucket()
    assert run(cfg, tmp_path) == 0
    keys = {o["Key"] for o in s3.list_objects_v2(Bucket=BUCKET)["Contents"]}
    assert keys == {f"opf/air/2026-10/{n}" for n in ("air.geojson", "air.kml", "manifest.json")} | {
        "opf/air/latest.json"}
    manifest = json.loads(s3.get_object(Bucket=BUCKET, Key="opf/air/2026-10/manifest.json")["Body"].read())
    assert manifest["communes"] == 2
    latest = json.loads(s3.get_object(Bucket=BUCKET, Key="opf/air/latest.json")["Body"].read())
    assert latest["period"] == "2026-10"


def test_unknown_bucket_fails_at_the_distribution_step(env, capsys):
    cfg, tmp_path = env  # le bucket n'a pas été créé
    assert run(cfg, tmp_path) == 1
    printed = capsys.readouterr().out
    assert "build" in printed and "distribute" in printed and "NoSuchBucket" in printed
    assert (tmp_path / "ws" / "air" / "2026-10").exists()  # produits conservés pour rejouer la distribution


def test_chain_reads_an_annual_raster_from_s3_and_publishes_to_s3(env):
    """Parcours VIIRS : raster annuel déposé dans S3 (`inputs/vnl/vnl_{year}.tif`), lu puis résultat publié."""
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    cfg, tmp_path = env
    tif = tmp_path / "vnl_2025.tif"
    with rasterio.open(
        tif, "w", driver="GTiff", height=100, width=100, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(0.9, 43.4, 0.005, 0.005),  # sans nodata, comme VIIRS
    ) as dst:
        dst.write(np.full((100, 100), 3.0, dtype="float32"), 1)
    s3 = create_bucket()
    s3.upload_file(str(tif), BUCKET, "inputs/vnl/vnl_2025.tif")
    cfg.write_text(
        cfg.read_text().replace(
            "    method: nearest_station\n    path: " + f"{tmp_path}/pm10_{{period}}.csv\n    field: pm10\n    dims: [lon, lat]",
            f"    method: zonal_mean\n    url: s3://{BUCKET}/inputs/vnl/vnl_{{year}}.tif",
        )
        .replace("thresholds: [10, 20, 30, 40]", "thresholds: [1, 2, 4, 8]")
        .replace("fetch: {use: configured_sources}", f"fetch: {{use: configured_sources, params: {{cache_dir: {tmp_path}/cache}}}}")
    )
    assert main(["run", "--config", str(cfg), "--period", "2025", "--workspace", str(tmp_path / "ws")]) == 0
    manifest = json.loads(s3.get_object(Bucket=BUCKET, Key="opf/air/2025/manifest.json")["Body"].read())
    assert manifest["communes"] == 2 and manifest["period"] == "2025"
    inputs = manifest["inputs"]["pm10"]
    assert inputs["origin"] == f"s3://{BUCKET}/inputs/vnl/vnl_2025.tif" and inputs["status"] == "downloaded"
