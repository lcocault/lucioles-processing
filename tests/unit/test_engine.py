import numpy as np
import pandas as pd
import pytest

from lucioles_processing.config import IndicatorSpec, SourceConfig
from lucioles_processing.engine import SpatialIndicatorEngine
from lucioles_processing.export import kml_color


def test_nearest_station(communes, tmp_path):
    csv = tmp_path / "s.csv"
    pd.DataFrame(
        {"lon": [1.05, 1.25], "lat": [43.05, 43.25], "pm10": [10.0, 50.0], "valid": [1, 1]}
    ).to_csv(csv, sep=";", index=False)
    src = SourceConfig("pm10", "nearest_station", path=str(csv), field="pm10", dims=["lon", "lat"])
    values = SpatialIndicatorEngine(communes).extract(src, csv)
    assert values.tolist() == [10.0, 50.0]


def test_nearest_station_rejects_non_csv(communes, tmp_path):
    src = SourceConfig("x", "nearest_station", path="a.tif", field="v", dims=["a", "b"])
    with pytest.raises(ValueError, match="csv"):
        SpatialIndicatorEngine(communes).extract(src, tmp_path / "a.tif")


def test_zonal_mean_rejects_unknown_format(communes, tmp_path):
    src = SourceConfig("x", "zonal_mean", path="a.xyz")
    with pytest.raises(ValueError, match="non supporté"):
        SpatialIndicatorEngine(communes).extract(src, tmp_path / "a.xyz")


def test_zonal_mean_raster(communes, tmp_path):
    import rasterio
    from rasterio.transform import from_origin

    tif = tmp_path / "r.tif"
    data = np.full((100, 100), 20.0, dtype="float32")
    with rasterio.open(
        tif, "w", driver="GTiff", height=100, width=100, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(0.9, 43.4, 0.005, 0.005), nodata=-9999,
    ) as dst:
        dst.write(data, 1)
    src = SourceConfig("no2", "zonal_mean", path=str(tif))
    values = SpatialIndicatorEngine(communes).extract(src, tif)
    assert values.tolist() == [20.0, 20.0]


def test_compute_indicator_levels_and_missing(communes):
    engine = SpatialIndicatorEngine(communes)
    spec = IndicatorSpec(name="ind", weights={"a": 1.0}, thresholds=[10, 20, 30, 40])
    engine.compute_indicator(spec, {"a": pd.Series([5.0, np.nan], index=communes.index)})
    assert engine.gdf["opf_level"].iloc[0] == 0
    assert pd.isna(engine.gdf["opf_level"].iloc[1])


@pytest.mark.parametrize("value,level", [(9.9, 0), (10, 1), (35, 3), (100, 4)])
def test_levels(communes, value, level):
    engine = SpatialIndicatorEngine(communes)
    spec = IndicatorSpec(name="ind", weights={"a": 1.0}, thresholds=[10, 20, 30, 40])
    engine.compute_indicator(spec, {"a": pd.Series([value, value], index=communes.index)})
    assert engine.gdf["opf_level"].iloc[0] == level


def test_kml_color():
    assert kml_color(0) == "ff57d371"  # #71d357 en aabbggrr
    assert kml_color(None) == kml_color(float("nan"))
