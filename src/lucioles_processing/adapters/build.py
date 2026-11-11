"""Étape 5 : production des fichiers de diffusion (cartes)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timezone

import geopandas as gpd
import pandas as pd
import shapely

from ..config import ChainDefinition
from ..constants import ADMIN_CODE_COLUMN, ADMIN_DEPT_COLUMN, ADMIN_NAME_COLUMN
from ..domain.model import Dataset, IndicatorValue, ProductFile
from ..domain.ports import ProductBuilder, StepContext
from . import export

FORMATS = ("gpkg", "geojson", "kml", "pmtiles")


class MapFilesBuilder(ProductBuilder):
    """GeoPackage, GeoJSON, KML colorisé, PMTiles et manifeste de traçabilité."""

    def __init__(self, definition: ChainDefinition, formats: Sequence[str] = FORMATS):
        unknown = set(formats) - set(FORMATS)
        if unknown:
            raise ValueError(f"Formats inconnus : {sorted(unknown)} (attendu : {list(FORMATS)})")
        self.definition = definition
        self.formats = tuple(formats)

    def build(
        self, ctx: StepContext, dataset: Dataset, values: Sequence[IndicatorValue]
    ) -> Sequence[ProductFile]:
        gdf = self._to_geodataframe(dataset, values)
        name, out = self.definition.indicator.name, ctx.directory("products")
        formats = self.formats
        products: list[ProductFile] = []

        def add(fmt: str, filename: str) -> None:
            products.append(ProductFile(filename, out / filename, fmt))

        if "gpkg" in formats:
            export.export_geopackage(gdf, out / f"{name}.gpkg")
            add("gpkg", f"{name}.gpkg")
        if "geojson" in formats or "pmtiles" in formats:
            export.export_geojson(gdf, out / f"{name}.geojson")
            if "geojson" in formats:
                add("geojson", f"{name}.geojson")
        if "kml" in formats:
            export.export_kml(gdf, out / f"{name}.kml", name)
            add("kml", f"{name}.kml")
        if "pmtiles" in formats and export.export_pmtiles(out / f"{name}.geojson", out / f"{name}.pmtiles"):
            add("pmtiles", f"{name}.pmtiles")

        (out / "manifest.json").write_text(
            json.dumps(
                {
                    "chain": ctx.chain,
                    "indicator": name,
                    "period": str(ctx.period),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "communes": len(gdf),
                    "missing": int(gdf["opf_level"].isna().sum()),
                    "sources": {n: str(s.path or s.url) for n, s in self.definition.sources.items()},
                    "inputs": {
                        name: {
                            "origin": f.origin, "status": f.status, "version": f.version, "sha256": f.sha256,
                        }
                        for name, f in dataset.inputs.items()
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        add("json", "manifest.json")
        return products

    @staticmethod
    def _to_geodataframe(dataset: Dataset, values: Sequence[IndicatorValue]) -> gpd.GeoDataFrame:
        by_code = {v.territory_code: v for v in values}
        rows = []
        for t in dataset.territories:
            row = {ADMIN_CODE_COLUMN: t.code, ADMIN_NAME_COLUMN: t.name, ADMIN_DEPT_COLUMN: t.department}
            for source in dataset.sources:
                v = dataset.value(source, t.code)
                row[f"val_{source}"] = float("nan") if v is None else v
            value = by_code[t.code]
            row[value.indicator] = float("nan") if value.value is None else value.value
            row["opf_level"] = value.level
            row["geometry"] = shapely.from_wkt(t.geometry_wkt)
            rows.append(row)
        gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
        gdf["opf_level"] = pd.array(gdf["opf_level"], dtype="Int64")
        return gdf
