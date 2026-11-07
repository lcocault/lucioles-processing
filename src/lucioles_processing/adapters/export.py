"""Exports cartographiques : GeoPackage, GeoJSON, KML colorisé, PMTiles."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

import geopandas as gpd
import matplotlib.colors as mcolors
import pandas as pd
import simplekml

from ..constants import ADMIN_NAME_COLUMN, NO_DATA_COLOR, OPF_COLORS

log = logging.getLogger(__name__)


def kml_color(level) -> str:
    """Niveau OPF (0..4, ou NA) -> couleur KML 'aabbggrr' opaque."""
    hex_color = NO_DATA_COLOR if pd.isna(level) else OPF_COLORS[int(level)]
    r, g, b = (int(x * 255) for x in mcolors.to_rgb(hex_color))
    return f"ff{b:02x}{g:02x}{r:02x}"


def export_geopackage(gdf: gpd.GeoDataFrame, path: Path) -> None:
    gdf.to_file(path, driver="GPKG")


def export_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    gdf.to_file(path, driver="GeoJSON")


def export_kml(gdf: gpd.GeoDataFrame, path: Path, indicator_name: str) -> None:
    kml = simplekml.Kml()
    for _, row in gdf.iterrows():
        geom = row.geometry
        name = str(row.get(ADMIN_NAME_COLUMN, ""))
        if geom.geom_type == "Polygon":
            parts, shape = [geom], kml.newpolygon(name=name)
            polys = [shape]
        elif geom.geom_type == "MultiPolygon":
            parts, shape = list(geom.geoms), kml.newmultigeometry(name=name)
            polys = [shape.newpolygon() for _ in parts]
        else:
            continue
        for poly, part in zip(polys, parts):
            poly.outerboundaryis = list(part.exterior.coords)
            poly.innerboundaryis = [list(ring.coords) for ring in part.interiors]
        shape.style.polystyle.color = kml_color(row["opf_level"])
        shape.style.polystyle.fill = 1
        shape.style.linestyle.width = 1
        shape.description = f"Commune : {name}<br/>{indicator_name} : {row[indicator_name]}"
    kml.save(str(path))


def export_pmtiles(geojson: Path, out: Path) -> bool:
    """GeoJSON -> MBTiles (tippecanoe) -> PMTiles (pmtiles). False si les binaires manquent."""
    if not (shutil.which("tippecanoe") and shutil.which("pmtiles")):
        log.warning("tippecanoe/pmtiles introuvables : export PMTiles ignoré")
        return False
    mbtiles = out.with_suffix(".mbtiles")
    subprocess.run(
        ["tippecanoe", "-o", str(mbtiles), "-zg", "--drop-densest-as-needed", "--force", str(geojson)],
        check=True,
    )
    subprocess.run(["pmtiles", "convert", str(mbtiles), str(out)], check=True)
    mbtiles.unlink()
    return True
