"""Chargement du fond administratif (communes)."""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import geopandas as gpd

from ..config import BoundariesConfig

log = logging.getLogger(__name__)


def load_admin(path: str | Path, boundaries: BoundariesConfig) -> gpd.GeoDataFrame:
    """Charge les communes, filtrées par départements, en EPSG:4326 (lon/lat).

    Les champs du fichier d'entrée sont décrits par `boundaries` ; le résultat les expose sous les noms
    internes `code`, `name` et `department`. On travaille en degrés car les stations sont en degrés.
    """
    gdf = gpd.read_file(path)
    for role, column in (("code_field", boundaries.code_field), ("name_field", boundaries.name_field)):
        if column not in gdf.columns:
            raise ValueError(
                f"[boundaries] champ '{column}' ({role}) absent de {Path(path).name} "
                f"(champs disponibles : {sorted(c for c in gdf.columns if c != 'geometry')})"
            )
    if boundaries.departments:
        if boundaries.department_field not in gdf.columns:
            raise ValueError(f"[boundaries] champ '{boundaries.department_field}' (department_field) absent")
        gdf = gdf[gdf[boundaries.department_field].astype(str).isin(boundaries.departments)]
        if gdf.empty:
            raise ValueError(f"Aucune commune pour les départements {boundaries.departments}")

    gdf = gdf.rename(
        columns={boundaries.code_field: "code", boundaries.name_field: "name"}
        | ({boundaries.department_field: "department"} if boundaries.department_field in gdf.columns else {})
    )
    if "department" not in gdf.columns:
        gdf["department"] = ""
    gdf["code"] = gdf["code"].astype(str)
    if gdf["code"].duplicated().any():
        raise ValueError(f"[boundaries] codes de communes en double dans le champ '{boundaries.code_field}'")
    log.info("%d communes chargées", len(gdf))
    return gdf[["code", "name", "department", "geometry"]].to_crs("EPSG:4326").copy()


def centroids(gdf: gpd.GeoDataFrame) -> list[tuple[float, float]]:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)  # centroïdes en CRS géographique
        c = gdf.geometry.centroid
    return list(zip(c.x, c.y))
