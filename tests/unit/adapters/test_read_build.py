import json

import geopandas as gpd
import pandas as pd
import pytest
import shapely

from lucioles_processing.adapters.build import MapFilesBuilder
from lucioles_processing.adapters.calculate import WeightedSumCalculator
from lucioles_processing.adapters.read import CommuneAggregationReader
from lucioles_processing.config import parse_chain_definition
from lucioles_processing.domain.model import Period
from lucioles_processing.domain.ports import StepContext
from tests.doubles import raw_definition

PERIOD = Period(2026, 10)


@pytest.fixture
def admin(communes, tmp_path):
    path = tmp_path / "admin.gpkg"
    communes.to_file(path, driver="GPKG")
    return path


@pytest.fixture
def definition(tmp_path):
    raw = raw_definition()
    raw["indicator"].update(weights={"pm10": 1.0}, thresholds=[10, 20, 30, 40])
    raw["sources"] = {
        "pm10": {"method": "nearest_station", "path": str(tmp_path / "pm10.csv"),
                 "field": "pm10", "dims": ["lon", "lat"]}
    }
    return parse_chain_definition(raw)


@pytest.fixture
def pm10(tmp_path):
    path = tmp_path / "pm10.csv"
    pd.DataFrame({"lon": [1.05, 1.25], "lat": [43.05, 43.25], "pm10": [5.0, 45.0]}).to_csv(
        path, sep=";", index=False
    )
    return path


def ctx(tmp_path):
    return StepContext("run1", "demo", PERIOD, tmp_path / "ws")


def test_reader_maps_to_internal_model(admin, definition, pm10, tmp_path):
    reader = CommuneAggregationReader(definition.sources, admin, ["31"])
    ds = reader.read(ctx(tmp_path), {"pm10": pm10})
    assert [t.name for t in ds.territories] == ["Commune A", "Commune B"]
    assert [t.code for t in ds.territories] == ["0", "1"]  # pas de colonne code_insee : l'index
    assert ds.sources == ("pm10",)
    assert [ds.value("pm10", c) for c in ("0", "1")] == [5.0, 45.0]
    assert ds.period == PERIOD


def test_reader_keeps_geometry_exactly(admin, definition, pm10, communes, tmp_path):
    ds = CommuneAggregationReader(definition.sources, admin, []).read(ctx(tmp_path), {"pm10": pm10})
    for territory, geom in zip(ds.territories, communes.geometry, strict=True):
        assert shapely.from_wkt(territory.geometry_wkt).equals_exact(geom, 0)


def test_reader_missing_data_becomes_none(admin, definition, tmp_path):
    csv = tmp_path / "pm10.csv"
    pd.DataFrame({"lon": [1.05, 1.25], "lat": [43.05, 43.25], "pm10": [float("nan"), 45.0]}).to_csv(
        csv, sep=";", index=False
    )
    ds = CommuneAggregationReader(definition.sources, admin, []).read(ctx(tmp_path), {"pm10": csv})
    assert ds.value("pm10", "0") is None


def test_reader_unknown_department(admin, definition, pm10, tmp_path):
    reader = CommuneAggregationReader(definition.sources, admin, ["99"])
    with pytest.raises(ValueError, match="Aucune commune"):
        reader.read(ctx(tmp_path), {"pm10": pm10})


def read_and_calculate(admin, definition, pm10, tmp_path):
    c = ctx(tmp_path)
    ds = CommuneAggregationReader(definition.sources, admin, []).read(c, {"pm10": pm10})
    return ds, list(WeightedSumCalculator(definition.indicator).calculate(c, ds))


def test_builder_produces_requested_files(admin, definition, pm10, tmp_path):
    ds, values = read_and_calculate(admin, definition, pm10, tmp_path)
    builder = MapFilesBuilder(definition, ["gpkg", "geojson", "kml"])
    products = builder.build(ctx(tmp_path), ds, values)
    assert [p.name for p in products] == ["ind.gpkg", "ind.geojson", "ind.kml", "manifest.json"]
    assert all(p.path.exists() for p in products)
    manifest = json.loads(products[-1].path.read_text())
    assert manifest["communes"] == 2 and manifest["missing"] == 0 and manifest["period"] == "2026-10"


def test_builder_geodata_matches_values(admin, definition, pm10, tmp_path):
    ds, values = read_and_calculate(admin, definition, pm10, tmp_path)
    [gpkg, *_] = MapFilesBuilder(definition, ["gpkg"]).build(ctx(tmp_path), ds, values)
    gdf = gpd.read_file(gpkg.path)
    assert gdf["val_pm10"].tolist() == [5.0, 45.0]
    assert gdf["ind"].tolist() == [5.0, 45.0]
    assert gdf["opf_level"].tolist() == [0, 4]
    assert gdf["nom_officiel"].tolist() == ["Commune A", "Commune B"]


def test_builder_missing_level_is_null(admin, definition, tmp_path):
    csv = tmp_path / "pm10.csv"
    pd.DataFrame({"lon": [1.05], "lat": [43.05], "pm10": [float("nan")]}).to_csv(csv, sep=";", index=False)
    ds, values = read_and_calculate(admin, definition, csv, tmp_path)
    [gpkg, *_] = MapFilesBuilder(definition, ["gpkg"]).build(ctx(tmp_path), ds, values)
    assert gpd.read_file(gpkg.path)["opf_level"].isna().all()


def test_builder_rejects_unknown_format(definition):
    with pytest.raises(ValueError, match="Formats inconnus"):
        MapFilesBuilder(definition, ["docx"])
