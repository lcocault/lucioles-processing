"""Extraction d'une fenêtre géographique d'un grand raster (par exemple VIIRS VNL mondial, ~11 Go).

La lecture est fenêtrée : seules les lignes concernées sont lues, le raster n'est jamais chargé en entier.
Le résultat garde la géoréférence, est compressé et porte sa provenance dans ses métadonnées.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import rasterio
from rasterio.errors import WindowError
from rasterio.windows import Window, from_bounds

#: Emprises prédéfinies (ouest, sud, est, nord) en degrés, avec une petite marge ajoutée à l'extraction.
REGIONS: dict[str, tuple[float, float, float, float]] = {
    "france": (-5.5, 41.2, 9.8, 51.3),  # France métropolitaine, Corse comprise
    "haute-garonne": (0.35, 42.6, 2.05, 43.95),
}

Bbox = tuple[float, float, float, float]


@dataclass(frozen=True)
class ExtractResult:
    path: Path
    width: int
    height: int
    bbox: Bbox
    size_bytes: int


def resolve_bbox(bbox: Bbox | None, region: str | None) -> Bbox:
    if (bbox is None) == (region is None):
        raise ValueError("Indiquer exactement une emprise : --bbox OUEST SUD EST NORD ou --region")
    if region is not None:
        if region not in REGIONS:
            raise ValueError(f"Région inconnue '{region}' (disponibles : {', '.join(sorted(REGIONS))})")
        return REGIONS[region]
    assert bbox is not None
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError(f"Emprise invalide {bbox} (attendu : ouest < est, sud < nord, en degrés)")
    return bbox


def extract_window(source: Path, destination: Path, bbox: Bbox, margin: float = 0.05) -> ExtractResult:
    """Écrit dans `destination` la partie de `source` comprise dans `bbox` (élargie de `margin` degrés)."""
    west, south, east, north = bbox
    destination = Path(destination)
    with rasterio.open(source) as src:
        if src.crs is None or not src.crs.is_geographic:
            raise ValueError(f"{source} : seuls les rasters en coordonnées géographiques sont pris en charge")
        window = from_bounds(west - margin, south - margin, east + margin, north + margin, transform=src.transform)
        window = Window(
            math.floor(window.col_off), math.floor(window.row_off),
            math.ceil(window.width) + 1, math.ceil(window.height) + 1,
        )
        try:
            window = window.intersection(Window(0, 0, src.width, src.height))
        except WindowError as exc:
            raise ValueError(f"L'emprise {bbox} est hors du raster {source}") from exc
        data = src.read(1, window=window)
        transform = src.window_transform(window)
        float_data = data.dtype.kind == "f"
        destination.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(
            destination, "w", driver="GTiff", width=data.shape[1], height=data.shape[0], count=1,
            dtype=data.dtype, crs=src.crs, transform=transform, nodata=src.nodata,
            compress="deflate", predictor=3 if float_data else 2, tiled=True, blockxsize=256, blockysize=256,
        ) as dst:
            dst.write(data, 1)
            dst.update_tags(
                SOURCE_FILE=Path(source).name,
                EXTRACT_BBOX=f"{west},{south},{east},{north}",
                EXTRACT_MARGIN_DEG=str(margin),
            )
    return ExtractResult(destination, data.shape[1], data.shape[0], bbox, destination.stat().st_size)
