"""Téléchargement depuis S3 (`s3://bucket/clé`) : mêmes garanties que le téléchargement HTTP."""

import boto3
import pytest
from botocore.exceptions import EndpointConnectionError
from moto import mock_aws

from lucioles_processing.adapters.collect import collect
from lucioles_processing.adapters.download import download
from lucioles_processing.config import SourceConfig
from lucioles_processing.domain.model import Period

BUCKET, KEY = "lucioles-test", "inputs/vnl/vnl_2025_france.tif"
URL = f"s3://{BUCKET}/{KEY}"


@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name="eu-west-3")
        client.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
        client.put_object(Bucket=BUCKET, Key=KEY, Body=b"raster-v1")
        yield client


def test_first_download_then_unchanged_without_fetching_again(s3, tmp_path):
    target = tmp_path / "vnl.tif"
    first = download(URL, target)
    second = download(URL, target)
    assert (first.status, second.status) == ("downloaded", "unchanged")
    assert target.read_bytes() == b"raster-v1"
    assert first.origin == URL and first.sha256 and first.version
    assert (tmp_path / "vnl.tif.meta.json").exists() and not list(tmp_path.glob("*.part"))


def test_changed_object_is_replaced(s3, tmp_path):
    target = tmp_path / "vnl.tif"
    download(URL, target)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=b"raster-v2-plus-long")
    assert download(URL, target).status == "downloaded"
    assert target.read_bytes() == b"raster-v2-plus-long"


def test_refresh_never_uses_the_copy_without_calling_s3(tmp_path):
    target = tmp_path / "vnl.tif"
    with mock_aws():
        client = boto3.client("s3", region_name="eu-west-3")
        client.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
        client.put_object(Bucket=BUCKET, Key=KEY, Body=b"raster-v1")
        download(URL, target)
    # hors de moto : aucun appel réseau ne doit être tenté
    assert download(URL, target, refresh="never").status == "cached"


def test_missing_object_is_an_error_even_with_a_copy(s3, tmp_path):
    target = tmp_path / "vnl.tif"
    download(URL, target)
    s3.delete_object(Bucket=BUCKET, Key=KEY)
    with pytest.raises(OSError, match="introuvable|404|403"):
        download(URL, target)
    assert target.read_bytes() == b"raster-v1"


def test_unreachable_s3_with_a_copy_is_unverified(s3, tmp_path):
    target = tmp_path / "vnl.tif"
    download(URL, target)

    class Down:
        def head_object(self, **_):
            raise EndpointConnectionError(endpoint_url="https://s3.example")

    assert download(URL, target, s3_client=Down()).status == "unverified"
    with pytest.raises(OSError):
        download(URL, tmp_path / "absent.tif", s3_client=Down())


@pytest.mark.parametrize("url", ["s3://", "s3://bucket", "s3:///cle", "s3://bucket/"])
def test_invalid_s3_url(url, tmp_path):
    with pytest.raises(ValueError, match="URL S3 invalide"):
        download(url, tmp_path / "x.tif")


def test_source_with_s3_url_and_year_placeholder(s3, tmp_path):
    source = SourceConfig("light", "zonal_mean", url=f"s3://{BUCKET}/inputs/vnl/vnl_{{year}}_france.tif")
    fetched = collect(source, Period(2025), tmp_path)
    assert fetched.status == "downloaded" and fetched.path.read_bytes() == b"raster-v1"
    assert fetched.path == tmp_path / "2025" / "light" / "vnl_2025_france.tif"
