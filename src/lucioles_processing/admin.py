"""Chargement du fond administratif (communes ADMIN_EXPRESS)."""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import geopandas as gpd

from .constants import ADMIN_DEPT_COLUMN

log = logging.getLogger(__name__)


def load_admin(path: str | Path, departments: list[str] | None = None) -> gpd.GeoDataFrame:
    """Charge les communes, filtrées par départements, en EPSG:4326 (lon/lat).

    On travaille en degrés car les coordonnées des stations sont en degrés.
    """
    gdf = gpd.read_file(path)
    if departments:
        gdf = gdf[gdf[ADMIN_DEPT_COLUMN].isin(departments)]
        if gdf.empty:
            raise ValueError(f"Aucune commune pour les départements {departments}")
    log.info("%d communes chargées", len(gdf))
    return gdf.to_crs("EPSG:4326").copy()


def centroids(gdf: gpd.GeoDataFrame) -> list[tuple[float, float]]:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)  # centroïdes en CRS géographique
        c = gdf.geometry.centroid
    return list(zip(c.x, c.y))
