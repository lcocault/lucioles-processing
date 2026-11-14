import pandas as pd
import rasterio

from lucioles_processing.cli import main
from lucioles_processing.config import load_chain_definition
from lucioles_processing.domain.model import Period
from lucioles_processing.domain.run import Step
from lucioles_processing.sample_data import make_sample_data


def test_sample_data_files(tmp_path):
    tif, csv = make_sample_data(tmp_path / "in", Period(2026, 10))
    assert (tif.name, csv.name) == ("no2_2026-10.tif", "pm10_2026-10.csv")
    with rasterio.open(tif) as src:
        assert src.crs.to_string() == "EPSG:4326" and src.nodata == -9999
        data = src.read(1)
        assert 0 < data.mean() < 50 and src.bounds.left == 0.4
    df = pd.read_csv(csv, sep=";")
    assert list(df.columns) == ["longitude", "latitude", "pm10", "valid"] and len(df) == 25


def test_sample_data_is_deterministic(tmp_path):
    a = make_sample_data(tmp_path / "a", Period(2026, 10))[1].read_text()
    b = make_sample_data(tmp_path / "b", Period(2026, 10))[1].read_text()
    assert a == b


def test_cli_sample_data(tmp_path, capsys):
    assert main(["sample-data", "--output", str(tmp_path), "--period", "2026-10"]) == 0
    assert "SYNTHÉTIQUES" in capsys.readouterr().out
    assert (tmp_path / "pm10_2026-10.csv").exists()


def test_smoke_chain_is_valid_and_matches_the_sample_files(monkeypatch):
    monkeypatch.setenv("LUCIOLES_S3_BUCKET", "un-bucket")
    d = load_chain_definition("configs/smoke.yaml")
    assert d.steps[Step.DISTRIBUTE].params["bucket"] == "un-bucket"
    assert d.sources["no2"].path == "data/inputs/no2_{period}.tif"
    assert d.sources["pm10"].dims == ["longitude", "latitude"]
