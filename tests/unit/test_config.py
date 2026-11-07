import pytest

from lucioles_processing.collect import period_fields
from lucioles_processing.config import IndicatorSpec, SourceConfig, load_config


def test_example_config_loads():
    cfg = load_config("configs/air_quality.example.yaml")
    assert cfg.indicator.name == "air_quality"
    assert set(cfg.sources) == {"no2", "pm10"}


def test_unknown_method():
    with pytest.raises(ValueError, match="inconnue"):
        SourceConfig(name="x", method="magic", path="a.tif")


def test_nearest_station_requires_dims():
    with pytest.raises(ValueError, match="dims"):
        SourceConfig(name="x", method="nearest_station", path="a.csv", field="v")


def test_thresholds_must_be_sorted():
    with pytest.raises(ValueError):
        IndicatorSpec(name="i", weights={}, thresholds=[4, 3, 2, 1])


@pytest.mark.parametrize("bad", ["2026", "2026-13", "10-2026", "abc"])
def test_invalid_period(bad):
    with pytest.raises(ValueError, match="Période invalide"):
        period_fields(bad)


def test_period_fields():
    assert period_fields("2026-10") == {"period": "2026-10", "year": "2026", "month": "10"}
