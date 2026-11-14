"""Données d'exemple SYNTHÉTIQUES (Haute-Garonne) pour tester une chaîne de bout en bout.

Ces données ne représentent aucune mesure réelle : elles servent uniquement à vérifier une installation
(téléchargement des limites, calcul, production des fichiers, distribution).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin

from .domain.model import Period

#: Emprise de la Haute-Garonne (lon/lat) et centre de l'agglomération toulousaine
WEST, NORTH, EAST, SOUTH = 0.4, 43.95, 2.0, 42.6
TOULOUSE = (1.44, 43.60)


def make_sample_data(output_dir: Path, period: Period, seed: int = 1) -> list[Path]:
    """Écrit `no2_<période>.tif` et `pm10_<période>.csv` dans `output_dir` ; retourne les fichiers créés."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    step = 0.002
    width, height = round((EAST - WEST) / step), round((NORTH - SOUTH) / step)
    lon = WEST + (np.arange(width) + 0.5) * step
    lat = NORTH - (np.arange(height) + 0.5) * step
    grid_lon, grid_lat = np.meshgrid(lon, lat)
    no2 = 8 + 40 * np.exp(
        -(((grid_lon - TOULOUSE[0]) / 0.12) ** 2 + ((grid_lat - TOULOUSE[1]) / 0.09) ** 2)
    ) + rng.normal(0, 1.5, (height, width))
    tif = output_dir / f"no2_{period}.tif"
    with rasterio.open(
        tif, "w", driver="GTiff", height=height, width=width, count=1, dtype="float32", crs="EPSG:4326",
        transform=from_origin(WEST, NORTH, step, step), nodata=-9999, compress="deflate",
    ) as dst:
        dst.write(no2.astype("float32"), 1)

    stations = pd.DataFrame(
        {"longitude": rng.uniform(0.5, 1.9, 25), "latitude": rng.uniform(42.8, 43.9, 25)}
    )
    distance = np.hypot(stations.longitude - TOULOUSE[0], (stations.latitude - TOULOUSE[1]) * 1.3)
    stations["pm10"] = (12 + 35 * np.exp(-((distance / 0.25) ** 2)) + rng.normal(0, 2, 25)).round(1)
    stations["valid"] = 1
    csv = output_dir / f"pm10_{period}.csv"
    stations.to_csv(csv, sep=";", index=False)
    return [tif, csv]
