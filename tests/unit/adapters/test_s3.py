import json

import boto3
import pytest
from moto import mock_aws

from lucioles_processing.adapters.s3 import S3Distributor
from lucioles_processing.domain.model import Period, ProductFile
from lucioles_processing.domain.ports import StepContext

BUCKET = "lucioles-test"


@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name="eu-west-3")
        client.create_bucket(
            Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "eu-west-3"}
        )
        yield client


def products(tmp_path, content="v1"):
    out = []
    for name, fmt in (("air.kml", "kml"), ("air.geojson", "geojson"), ("air.gpkg", "gpkg"),
                      ("manifest.json", "json"), ("air.pmtiles", "pmtiles")):
        f = tmp_path / name
        f.write_text(content)
        out.append(ProductFile(name, f, fmt))
    return out


def ctx(tmp_path, period=None):
    period = period or Period(2026, 10)
    return StepContext("run", "air", period, tmp_path)


def keys(s3):
    return sorted(o["Key"] for o in s3.list_objects_v2(Bucket=BUCKET).get("Contents", []))


def test_publishes_under_chain_and_period(s3, tmp_path):
    S3Distributor(BUCKET, "opf/", client=s3).distribute(ctx(tmp_path), products(tmp_path))
    assert keys(s3) == sorted(
        [f"opf/air/2026-10/{n}" for n in ("air.kml", "air.geojson", "air.gpkg", "manifest.json", "air.pmtiles")]
        + ["opf/air/latest.json"]
    )


def test_content_types(s3, tmp_path):
    S3Distributor(BUCKET, client=s3).distribute(ctx(tmp_path), products(tmp_path))
    head = lambda n: s3.head_object(Bucket=BUCKET, Key=f"air/2026-10/{n}")["ContentType"]
    assert head("air.kml") == "application/vnd.google-earth.kml+xml"
    assert head("air.geojson") == "application/geo+json"
    assert head("manifest.json") == "application/json"


def test_without_prefix(s3, tmp_path):
    S3Distributor(BUCKET, client=s3).distribute(ctx(tmp_path), products(tmp_path)[:1])
    assert keys(s3) == ["air/2026-10/air.kml", "air/latest.json"]


def test_republishing_overwrites_idempotently(s3, tmp_path):
    dist = S3Distributor(BUCKET, client=s3)
    dist.distribute(ctx(tmp_path), products(tmp_path, "v1"))
    before = keys(s3)
    dist.distribute(ctx(tmp_path), products(tmp_path, "version 2"))
    assert keys(s3) == before
    assert s3.get_object(Bucket=BUCKET, Key="air/2026-10/air.kml")["Body"].read() == b"version 2"


def latest(s3):
    return json.loads(s3.get_object(Bucket=BUCKET, Key="air/latest.json")["Body"].read())


def test_latest_points_to_the_most_recent_period(s3, tmp_path):
    dist = S3Distributor(BUCKET, client=s3)
    dist.distribute(ctx(tmp_path, Period(2026, 9)), products(tmp_path))
    dist.distribute(ctx(tmp_path, Period(2026, 10)), products(tmp_path))
    info = latest(s3)
    assert info["period"] == "2026-10" and info["chain"] == "air"
    assert {f["key"] for f in info["files"]} >= {"air/2026-10/air.kml"}
    assert all(f["size"] > 0 for f in info["files"])


def test_replaying_an_older_period_does_not_move_latest_back(s3, tmp_path):
    dist = S3Distributor(BUCKET, client=s3)
    dist.distribute(ctx(tmp_path, Period(2026, 10)), products(tmp_path))
    dist.distribute(ctx(tmp_path, Period(2026, 8)), products(tmp_path))
    assert latest(s3)["period"] == "2026-10"
    assert "air/2026-08/air.kml" in keys(s3)  # mais la période rejouée est bien publiée


def test_missing_bucket_is_an_error(s3, tmp_path):
    with pytest.raises(Exception, match="NoSuchBucket"):
        S3Distributor("absent", client=s3).distribute(ctx(tmp_path), products(tmp_path)[:1])


def test_bucket_is_required():
    with pytest.raises(ValueError, match="bucket"):
        S3Distributor("")


def test_registry_builds_the_s3_distributor_and_requires_a_bucket():
    from lucioles_processing.adapters.registry import default_registry
    from lucioles_processing.config import parse_chain_definition
    from lucioles_processing.domain.run import Step
    from tests.doubles import raw_definition

    registry = default_registry()
    assert "s3" in registry.names(Step.DISTRIBUTE)
    base = {
        "fetch": {"use": "configured_sources"}, "read": {"use": "commune_aggregation"},
        "calculate": {"use": "weighted_sum"}, "build": {"use": "map_files"},
    }
    ok = parse_chain_definition(raw_definition(**base, distribute={
        "use": "s3", "params": {"bucket": BUCKET, "prefix": "opf", "region": "eu-west-3"}}))
    dist = registry.build(ok).distributor
    assert (dist.bucket, dist.prefix) == (BUCKET, "opf")
    bad = parse_chain_definition(raw_definition(**base, distribute={"use": "s3"}))
    with pytest.raises(ValueError, match="paramètre 'bucket' manquant"):
        registry.build(bad)
