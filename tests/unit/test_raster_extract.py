"""Extraction fenêtrée d'un raster mondial synthétique : géoréférence, valeurs, compression, erreurs."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from lucioles_processing.cli import main
from lucioles_processing.raster_extract import REGIONS, extract_window, resolve_bbox

STEP = 0.5  # raster « mondial » grossier : 720 x 280 pixels, de -180 à 180 et de -65 à 75


@pytest.fixture
def world(tmp_path):
    height, width = 280, 720
    data = (np.arange(height * width, dtype="float32").reshape(height, width)) / 1000.0
    path = tmp_path / "world.tif"
    with rasterio.open(
        path, "w", driver="GTiff", width=width, height=height, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(-180, 75, STEP, STEP),
    ) as dst:
        dst.write(data, 1)
    return path, data


def test_extracts_only_the_requested_area_with_georeferencing(world, tmp_path):
    path, data = world
    result = extract_window(path, tmp_path / "out" / "zone.tif", (0.0, 42.0, 2.0, 44.0), margin=0.0)
    with rasterio.open(result.path) as out, rasterio.open(path) as src:
        assert out.crs == src.crs and out.dtypes == ("float32",)
        assert out.width < 15 and out.height < 15  # une zone de 2 x 2 degrés, pas le raster entier
        assert out.bounds.left <= 0.0 and out.bounds.right >= 2.0
        assert out.bounds.bottom <= 42.0 and out.bounds.top >= 44.0
        # mêmes valeurs aux mêmes coordonnées
        lon, lat = 1.25, 43.25
        assert out.read(1)[out.index(lon, lat)] == data[src.index(lon, lat)]
    assert result.size_bytes == result.path.stat().st_size


def test_margin_enlarges_the_window(world, tmp_path):
    path, _ = world
    narrow = extract_window(path, tmp_path / "a.tif", (0.0, 42.0, 2.0, 44.0), margin=0.0)
    wide = extract_window(path, tmp_path / "b.tif", (0.0, 42.0, 2.0, 44.0), margin=1.0)
    assert wide.width > narrow.width and wide.height > narrow.height


def test_result_is_compressed_and_traceable(world, tmp_path):
    path, _ = world
    result = extract_window(path, tmp_path / "zone.tif", (0.0, 42.0, 2.0, 44.0))
    with rasterio.open(result.path) as out:
        assert out.compression.value == "DEFLATE"
        tags = out.tags()
    assert tags["SOURCE_FILE"] == "world.tif" and tags["EXTRACT_BBOX"] == "0.0,42.0,2.0,44.0"


def test_window_is_clipped_to_the_raster(world, tmp_path):
    path, _ = world
    result = extract_window(path, tmp_path / "edge.tif", (170.0, 70.0, 179.9, 74.9), margin=2.0)
    with rasterio.open(result.path) as out:
        assert out.bounds.right <= 180.0 + 1e-9 and out.bounds.top <= 75.0 + 1e-9


def test_area_outside_the_raster_is_an_error(world, tmp_path):
    path, _ = world
    with pytest.raises(ValueError, match="hors du raster"):
        extract_window(path, tmp_path / "x.tif", (10.0, -80.0, 12.0, -70.0), margin=0.0)


class TestBbox:
    def test_region_and_bbox_are_exclusive(self):
        with pytest.raises(ValueError, match="exactement une emprise"):
            resolve_bbox(None, None)
        with pytest.raises(ValueError, match="exactement une emprise"):
            resolve_bbox((0, 0, 1, 1), "france")

    def test_known_and_unknown_region(self):
        assert resolve_bbox(None, "haute-garonne") == REGIONS["haute-garonne"]
        with pytest.raises(ValueError, match="Région inconnue"):
            resolve_bbox(None, "atlantide")

    @pytest.mark.parametrize("bbox", [(2, 0, 1, 1), (0, 5, 1, 4), (-200, 0, 1, 1), (0, 0, 1, 91)])
    def test_invalid_bbox(self, bbox):
        with pytest.raises(ValueError, match="Emprise invalide"):
            resolve_bbox(bbox, None)


def test_cli_extract_raster(world, tmp_path, capsys):
    path, _ = world
    out = tmp_path / "fr.tif"
    code = main(["extract-raster", "--input", str(path), "--output", str(out), "--bbox", "0", "42", "2", "44"])
    assert code == 0 and out.exists()
    assert "pixels" in capsys.readouterr().out


def test_cli_extract_raster_errors_exit_2(world, tmp_path, capsys):
    path, _ = world
    assert main(["extract-raster", "--input", str(path), "--output", str(tmp_path / "x.tif")]) == 2
    assert main(["extract-raster", "--input", str(tmp_path / "absent.tif"), "--output", str(tmp_path / "x.tif"),
                 "--region", "france"]) == 2
    assert "Erreur" in capsys.readouterr().err
