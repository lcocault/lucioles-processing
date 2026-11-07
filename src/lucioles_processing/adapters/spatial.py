"""Agrégation spatiale des sources par commune.

Chaque source est agrégée par commune (`zonal_mean` ou `nearest_station`) ; une commune
sans donnée vaut NaN (et non 0).
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from scipy.spatial import cKDTree

from ..config import SourceConfig
from .admin import centroids

log = logging.getLogger(__name__)

VECTOR_EXT = {".gpkg", ".shp", ".geojson", ".json"}
RASTER_EXT = {".tif", ".tiff", ".nc"}


class SpatialExtractor:
    def __init__(self, communes: gpd.GeoDataFrame):
        self.gdf = communes.copy()
        self._centroids = centroids(self.gdf)

    # --- extraction -------------------------------------------------------

    def extract(self, source: SourceConfig, path: Path) -> pd.Series:
        ext = path.suffix.lower()
        if source.method == "zonal_mean":
            return self._zonal_mean(source, path, ext)
        return self._nearest_station(source, path, ext)

    def _zonal_mean(self, source: SourceConfig, path: Path, ext: str) -> pd.Series:
        if ext in VECTOR_EXT:
            ext_gdf = gpd.read_file(path)
            if source.condition:
                ext_gdf = ext_gdf.query(source.condition)
            ext_gdf = ext_gdf.to_crs(self.gdf.crs)
            joined = gpd.sjoin(
                self.gdf[["geometry"]],
                ext_gdf[[source.field, "geometry"]],
                how="left",
                predicate="intersects",
            )
            return joined.groupby(joined.index)[source.field].mean().reindex(self.gdf.index)

        if ext not in RASTER_EXT:
            raise ValueError(
                f"[{source.name}] format '{ext}' non supporté pour zonal_mean "
                f"(supportés : {sorted(VECTOR_EXT | RASTER_EXT)})"
            )
        connection = f"netcdf:{path}:{source.field}" if ext == ".nc" and source.field else str(path)
        with rasterio.open(connection) as src:
            communes = self.gdf.to_crs(src.crs or "EPSG:4326")
            values = [self._raster_mean(src, geom, source) for geom in communes.geometry]
        return pd.Series(values, index=self.gdf.index, dtype="float64")

    @staticmethod
    def _raster_mean(src, geom, source: SourceConfig) -> float:
        try:
            image, _ = mask(src, [geom], crop=True, all_touched=True)
        except ValueError:  # commune hors de l'emprise du raster
            return np.nan
        data = image[0]
        valid = ~np.isnan(data)
        if src.nodata is not None:
            valid &= data != src.nodata
        if source.condition:
            valid &= _eval_condition(source.condition, source.field, data)
        return float(data[valid].mean()) if valid.any() else np.nan

    def _nearest_station(self, source: SourceConfig, path: Path, ext: str) -> pd.Series:
        if ext != ".csv":
            raise ValueError(f"[{source.name}] nearest_station n'accepte que des .csv (reçu '{ext}')")
        df = pd.read_csv(path, sep=";", encoding="utf-8")
        if source.condition:
            df = df.query(source.condition)
        if df.empty:
            raise ValueError(f"[{source.name}] aucune station après application de la condition")
        _, idx = cKDTree(df[source.dims].values).query(self._centroids, k=1)
        return pd.Series(df.iloc[idx][source.field].values, index=self.gdf.index)


def _eval_condition(condition: str, field: str | None, data: np.ndarray) -> np.ndarray:
    """Évalue une condition booléenne numpy (ex. 'data > 0') sur la bande.

    `field` est accepté comme alias de `data`. L'évaluation est restreinte à numpy ; la
    configuration reste néanmoins une entrée de confiance (fichier versionné du dépôt).
    """
    expr = condition.replace(field, "data") if field else condition
    result = eval(expr, {"__builtins__": {}}, {"data": data, "np": np})
    return np.asarray(result, dtype=bool)
