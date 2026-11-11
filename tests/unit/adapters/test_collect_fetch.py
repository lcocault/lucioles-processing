import pytest

from lucioles_processing.adapters.collect import collect
from lucioles_processing.adapters.fetch import ConfiguredSourcesFetcher
from lucioles_processing.config import BoundariesConfig, SourceConfig
from lucioles_processing.domain.model import Period
from lucioles_processing.domain.ports import BOUNDARIES_KEY, StepContext

PERIOD = Period(2026, 10)


def ctx(tmp_path):
    return StepContext("r", "c", PERIOD, tmp_path / "ws")


def test_local_path_is_used_in_place(tmp_path):
    f = tmp_path / "no2_2026-10.tif"
    f.write_text("x")
    source = SourceConfig("no2", "zonal_mean", path=str(tmp_path / "no2_{period}.tif"))
    fetched = collect(source, PERIOD, tmp_path / "dl")
    assert fetched.path == f and fetched.status == "local"


def test_missing_local_file(tmp_path):
    source = SourceConfig("no2", "zonal_mean", path=str(tmp_path / "absent_{period}.tif"))
    with pytest.raises(FileNotFoundError, match="absent_2026-10"):
        collect(source, PERIOD, tmp_path)


def test_url_source_is_downloaded_then_verified(tmp_path, http_server):
    http_server.files["/pm10_2026_10.csv"] = b"a;b\n"
    source = SourceConfig("pm10", "zonal_mean", url=http_server.url("/pm10_{year}_{month}.csv?k=1"))
    first = collect(source, PERIOD, tmp_path)
    second = collect(source, PERIOD, tmp_path)
    assert first.path == second.path == tmp_path / "2026-10" / "pm10" / "pm10_2026_10.csv"
    assert (first.status, second.status) == ("downloaded", "unchanged")
    assert first.path.read_bytes() == b"a;b\n"


def make_fetcher(tmp_path, boundaries, cache=None, sources=None):
    return ConfiguredSourcesFetcher(sources or {}, boundaries, cache)


def test_fetcher_returns_boundaries_and_every_source(tmp_path):
    (tmp_path / "a.tif").write_text("x")
    (tmp_path / "communes.gpkg").write_text("x")
    sources = {"a": SourceConfig("a", "zonal_mean", path=str(tmp_path / "a.tif"))}
    raw = make_fetcher(tmp_path, BoundariesConfig(path=str(tmp_path / "communes.gpkg")), sources=sources).fetch(
        ctx(tmp_path)
    )
    assert set(raw) == {BOUNDARIES_KEY, "a"}
    assert raw["a"].path == tmp_path / "a.tif" and raw[BOUNDARIES_KEY].path == tmp_path / "communes.gpkg"


def test_fetcher_missing_local_boundaries(tmp_path):
    fetcher = make_fetcher(tmp_path, BoundariesConfig(path=str(tmp_path / "absent.gpkg")))
    with pytest.raises(FileNotFoundError, match="boundaries"):
        fetcher.fetch(ctx(tmp_path))


def test_fetcher_downloads_boundaries_into_cache_then_verifies(tmp_path, http_server):
    http_server.files["/communes.geojson"] = b"{}"
    boundaries = BoundariesConfig(url=http_server.url("/communes.geojson"))
    fetcher = make_fetcher(tmp_path, boundaries, cache=tmp_path / "cache")
    first = fetcher.fetch(ctx(tmp_path))[BOUNDARIES_KEY]
    second = fetcher.fetch(ctx(tmp_path))[BOUNDARIES_KEY]
    assert first.path == tmp_path / "cache" / "boundaries" / "communes.geojson"
    assert (first.status, second.status) == ("downloaded", "unchanged")
    assert http_server.requests[1][1]  # 2e appel : requête conditionnelle


def test_fetcher_detects_a_new_version_of_the_boundaries(tmp_path, http_server):
    http_server.files["/communes.geojson"] = b"{}"
    fetcher = make_fetcher(tmp_path, BoundariesConfig(url=http_server.url("/communes.geojson")), tmp_path / "c")
    first = fetcher.fetch(ctx(tmp_path))[BOUNDARIES_KEY]
    http_server.files["/communes.geojson"] = b'{"type": "FeatureCollection"}'
    second = fetcher.fetch(ctx(tmp_path))[BOUNDARIES_KEY]
    assert second.status == "downloaded" and second.sha256 != first.sha256
    assert second.path.read_bytes() == b'{"type": "FeatureCollection"}'


def test_fetcher_refresh_never_does_not_contact_the_server(tmp_path, http_server):
    http_server.files["/communes.geojson"] = b"{}"
    boundaries = BoundariesConfig(url=http_server.url("/communes.geojson"), refresh="never")
    fetcher = make_fetcher(tmp_path, boundaries, tmp_path / "c")
    fetcher.fetch(ctx(tmp_path))
    assert fetcher.fetch(ctx(tmp_path))[BOUNDARIES_KEY].status == "cached"
    assert http_server.count("/communes.geojson") == 1


def test_fetcher_uses_workspace_without_cache_dir(tmp_path, http_server):
    http_server.files["/communes.geojson"] = b"{}"
    boundaries = BoundariesConfig(url=http_server.url("/communes.geojson"))
    raw = make_fetcher(tmp_path, boundaries).fetch(ctx(tmp_path))
    assert (tmp_path / "ws" / "raw") in raw[BOUNDARIES_KEY].path.parents
