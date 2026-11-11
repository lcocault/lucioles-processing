import json

import geopandas as gpd
import pandas as pd
import pytest
import shapely

from lucioles_processing.adapters.build import MapFilesBuilder
from lucioles_processing.adapters.calculate import WeightedSumCalculator
from lucioles_processing.adapters.read import CommuneAggregationReader
from lucioles_processing.config import parse_chain_definition
from lucioles_processing.domain.model import FetchedFile, Period
from lucioles_processing.domain.ports import BOUNDARIES_KEY, StepContext
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
    raw["boundaries"] = {"path": str(tmp_path / "admin.gpkg")}
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


def raw(admin, csv):
    return {BOUNDARIES_KEY: FetchedFile.local(admin), "pm10": FetchedFile.local(csv)}


def ctx(tmp_path):
    return StepContext("run1", "demo", PERIOD, tmp_path / "ws")


def test_reader_maps_to_internal_model(admin, definition, pm10, tmp_path):
    reader = CommuneAggregationReader(definition.sources, definition.boundaries)
    ds = reader.read(ctx(tmp_path), raw(admin, pm10))
    assert [t.name for t in ds.territories] == ["Commune A", "Commune B"]
    assert [t.code for t in ds.territories] == ["31001", "31002"]
    assert {t.department for t in ds.territories} == {"31"}
    assert set(ds.inputs) == {BOUNDARIES_KEY, "pm10"}  # provenance conservée pour le manifeste
    assert ds.sources == ("pm10",)
    assert [ds.value("pm10", c) for c in ("31001", "31002")] == [5.0, 45.0]
    assert ds.period == PERIOD


def test_reader_keeps_geometry_exactly(admin, definition, pm10, communes, tmp_path):
    ds = CommuneAggregationReader(definition.sources, definition.boundaries).read(ctx(tmp_path), raw(admin, pm10))
    for territory, geom in zip(ds.territories, communes.geometry, strict=True):
        assert shapely.from_wkt(territory.geometry_wkt).equals_exact(geom, 0)


def test_reader_missing_data_becomes_none(admin, definition, tmp_path):
    csv = tmp_path / "pm10.csv"
    pd.DataFrame({"lon": [1.05, 1.25], "lat": [43.05, 43.25], "pm10": [float("nan"), 45.0]}).to_csv(
        csv, sep=";", index=False
    )
    ds = CommuneAggregationReader(definition.sources, definition.boundaries).read(ctx(tmp_path), raw(admin, csv))
    assert ds.value("pm10", "31001") is None


def test_reader_department_filter(admin, definition, pm10, tmp_path):
    definition.boundaries.departments = ["31"]
    ds = CommuneAggregationReader(definition.sources, definition.boundaries).read(
        ctx(tmp_path), raw(admin, pm10)
    )
    assert len(ds.territories) == 2


def test_reader_unknown_department(admin, definition, pm10, tmp_path):
    definition.boundaries.departments = ["99"]
    reader = CommuneAggregationReader(definition.sources, definition.boundaries)
    with pytest.raises(ValueError, match="Aucune commune"):
        reader.read(ctx(tmp_path), raw(admin, pm10))


def test_reader_with_other_field_names(communes, definition, pm10, tmp_path):
    other = tmp_path / "other.geojson"
    communes.rename(columns={"code_insee": "code", "nom_officiel": "nom", "code_insee_du_departement": "dep"}
                    ).to_file(other, driver="GeoJSON")
    definition.boundaries.code_field, definition.boundaries.name_field = "code", "nom"
    definition.boundaries.department_field = "dep"
    ds = CommuneAggregationReader(definition.sources, definition.boundaries).read(
        ctx(tmp_path), raw(other, pm10)
    )
    assert (ds.territories[0].code, ds.territories[0].name, ds.territories[0].department) == ("31001", "Commune A", "31")


def test_reader_missing_field_is_explicit(admin, definition, pm10, tmp_path):
    definition.boundaries.code_field = "inconnu"
    reader = CommuneAggregationReader(definition.sources, definition.boundaries)
    with pytest.raises(ValueError, match=r"champ 'inconnu'.*champs disponibles"):
        reader.read(ctx(tmp_path), raw(admin, pm10))


def test_reader_rejects_duplicate_codes(communes, definition, pm10, tmp_path):
    communes["code_insee"] = ["31001", "31001"]
    dup = tmp_path / "dup.gpkg"
    communes.to_file(dup, driver="GPKG")
    reader = CommuneAggregationReader(definition.sources, definition.boundaries)
    with pytest.raises(ValueError, match="en double"):
        reader.read(ctx(tmp_path), raw(dup, pm10))


def read_and_calculate(admin, definition, pm10, tmp_path):
    c = ctx(tmp_path)
    ds = CommuneAggregationReader(definition.sources, definition.boundaries).read(c, raw(admin, pm10))
    return ds, list(WeightedSumCalculator(definition.indicator).calculate(c, ds))


def test_builder_produces_requested_files(admin, definition, pm10, tmp_path):
    ds, values = read_and_calculate(admin, definition, pm10, tmp_path)
    builder = MapFilesBuilder(definition, ["gpkg", "geojson", "kml"])
    products = builder.build(ctx(tmp_path), ds, values)
    assert [p.name for p in products] == ["ind.gpkg", "ind.geojson", "ind.kml", "manifest.json"]
    assert all(p.path.exists() for p in products)
    manifest = json.loads(products[-1].path.read_text())
    assert manifest["communes"] == 2 and manifest["missing"] == 0 and manifest["period"] == "2026-10"
    assert set(manifest["inputs"]) == {"boundaries", "pm10"}
    assert manifest["inputs"]["boundaries"]["status"] == "local"


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
