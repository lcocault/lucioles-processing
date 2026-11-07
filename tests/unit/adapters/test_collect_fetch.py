import pytest

from lucioles_processing.adapters import collect as collect_module
from lucioles_processing.adapters.collect import collect
from lucioles_processing.adapters.fetch import ConfiguredSourcesFetcher
from lucioles_processing.config import SourceConfig
from lucioles_processing.domain.model import Period
from lucioles_processing.domain.ports import StepContext

PERIOD = Period(2026, 10)


def test_local_path_is_used_in_place(tmp_path):
    f = tmp_path / "no2_2026-10.tif"
    f.write_text("x")
    source = SourceConfig("no2", "zonal_mean", path=str(tmp_path / "no2_{period}.tif"))
    assert collect(source, PERIOD, tmp_path / "dl") == f


def test_missing_local_file(tmp_path):
    source = SourceConfig("no2", "zonal_mean", path=str(tmp_path / "absent_{period}.tif"))
    with pytest.raises(FileNotFoundError, match="absent_2026-10"):
        collect(source, PERIOD, tmp_path)


def test_url_is_downloaded_once(tmp_path, monkeypatch):
    calls = []

    def fake_retrieve(url, dest):
        calls.append(url)
        dest.write_text("data")

    monkeypatch.setattr(collect_module.urllib.request, "urlretrieve", fake_retrieve)
    source = SourceConfig("pm10", "zonal_mean", url="https://x.org/pm10_{year}_{month}.csv?k=1")
    first = collect(source, PERIOD, tmp_path)
    second = collect(source, PERIOD, tmp_path)
    assert first == second == tmp_path / "2026-10" / "pm10" / "pm10_2026_10.csv"
    assert calls == ["https://x.org/pm10_2026_10.csv?k=1"]
    assert not list(tmp_path.rglob("*.part"))


def test_fetcher_returns_every_source(tmp_path):
    (tmp_path / "a.tif").write_text("x")
    sources = {"a": SourceConfig("a", "zonal_mean", path=str(tmp_path / "a.tif"))}
    ctx = StepContext("r", "c", PERIOD, tmp_path / "ws")
    raw = ConfiguredSourcesFetcher(sources).fetch(ctx)
    assert raw == {"a": tmp_path / "a.tif"}


def test_fetcher_downloads_into_workspace_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(collect_module.urllib.request, "urlretrieve", lambda u, d: d.write_text("x"))
    sources = {"p": SourceConfig("p", "zonal_mean", url="https://x.org/p.csv")}
    ctx = StepContext("r", "c", PERIOD, tmp_path / "ws")
    raw = ConfiguredSourcesFetcher(sources).fetch(ctx)
    assert (tmp_path / "ws" / "raw") in raw["p"].parents


def test_fetcher_uses_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(collect_module.urllib.request, "urlretrieve", lambda u, d: d.write_text("x"))
    sources = {"p": SourceConfig("p", "zonal_mean", url="https://x.org/p.csv")}
    ctx = StepContext("r", "c", PERIOD, tmp_path / "ws")
    raw = ConfiguredSourcesFetcher(sources, tmp_path / "cache").fetch(ctx)
    assert (tmp_path / "cache") in raw["p"].parents
