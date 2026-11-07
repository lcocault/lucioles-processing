"""Orchestration d'un run : collecte -> calcul -> exports, pour un indicateur et une période."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from . import export
from .admin import load_admin
from .collect import collect, period_fields
from .config import load_config
from .engine import SpatialIndicatorEngine

log = logging.getLogger(__name__)

FORMATS = ("gpkg", "geojson", "kml", "pmtiles")


def run(
    config_path: Path,
    period: str,
    admin_path: Path,
    output_dir: Path,
    cache_dir: Path,
    formats: tuple[str, ...] = FORMATS,
) -> Path:
    """Exécute le traitement et retourne le dossier de sortie `<output>/<indicateur>/<période>/`."""
    period_fields(period)  # valide le format tôt
    cfg = load_config(config_path)
    name = cfg.indicator.name

    engine = SpatialIndicatorEngine(load_admin(admin_path, cfg.departments))
    extracted = {}
    for source in cfg.sources.values():
        log.info("Source : %s", source.name)
        extracted[source.name] = engine.extract(source, collect(source, period, cache_dir))
    engine.compute_indicator(cfg.indicator, extracted)

    out = output_dir / name / period
    out.mkdir(parents=True, exist_ok=True)
    if "gpkg" in formats:
        export.export_geopackage(engine.gdf, out / f"{name}.gpkg")
    if "geojson" in formats or "pmtiles" in formats:
        export.export_geojson(engine.gdf, out / f"{name}.geojson")
    if "kml" in formats:
        export.export_kml(engine.gdf, out / f"{name}.kml", name)
    if "pmtiles" in formats:
        export.export_pmtiles(out / f"{name}.geojson", out / f"{name}.pmtiles")

    # Traçabilité : ce qui a été produit, quand, à partir de quoi
    (out / "manifest.json").write_text(
        json.dumps(
            {
                "indicator": name,
                "period": period,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "communes": len(engine.gdf),
                "missing": int(engine.gdf["opf_level"].isna().sum()),
                "config": str(config_path),
                "sources": {n: str(s.path or s.url) for n, s in cfg.sources.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log.info("Terminé : %s", out)
    return out
