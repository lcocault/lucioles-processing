"""Interface en ligne de commande : `lucioles run ...`."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

import psycopg
import rasterio.errors

from .adapters.postgres.database import (
    ConfigurationError,
    Database,
    SchemaOutdatedError,
    database_url,
)
from .adapters.postgres.run_history import PostgresRunListener
from .adapters.registry import default_registry
from .application.executor import ChainExecutor
from .config import load_chain_definition
from .domain.model import Period
from .domain.run import ChainRun, Status

ICONS = {
    Status.SUCCEEDED: "OK", Status.FAILED: "ÉCHEC", Status.SKIPPED: "ignorée",
    Status.RUNNING: "en cours", Status.PENDING: "en attente",
}


def format_run(run: ChainRun) -> str:
    lines = [f"Chaîne {run.chain} — {run.period} — {ICONS[run.status]} (exécution {run.id})"]
    for s in run.steps:
        duration = f" {s.duration:.1f}s" if s.duration is not None else ""
        error = f" : {s.error}" if s.error else ""
        lines.append(f"  {s.step.value:<10} {s.implementation:<20} {ICONS[s.status]}{duration}{error}")
    return "\n".join(lines)


def resolve_period(text: str, today: date | None = None) -> Period:
    """`AAAA-MM` ou `AAAA`, ou `previous-month`/`current-month`/`previous-year`/`current-year` (tâches planifiées)."""
    today = today or date.today()
    if text == "current-year":
        return Period.of_year(today)
    if text == "previous-year":
        return Period.of_year(today).previous()
    if text == "current-month":
        return Period.of_month(today)
    if text == "previous-month":
        return Period.of_month(today).previous()
    return Period.parse(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lucioles", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="Exécute une chaîne de traitement pour une période")
    p.add_argument("--config", type=Path, required=True, help="Définition YAML de la chaîne")
    p.add_argument("--period", required=True, help="Période AAAA-MM ou AAAA, previous-month/current-month, previous-year/current-year")
    p.add_argument("--workspace", type=Path, default=Path("workspace"), help="Racine des espaces de travail")
    p.add_argument("-v", "--verbose", action="store_true")

    sd = sub.add_parser("sample-data", help="Écrit des données d'exemple synthétiques (test d'installation)")
    sd.add_argument("--output", type=Path, default=Path("data/inputs"))
    sd.add_argument("--period", default="current-month", help="Période AAAA-MM ou AAAA, previous-month/current-month, previous-year/current-year")

    ex = sub.add_parser("extract-raster", help="Extrait une zone d'un grand raster (par exemple VIIRS mondial)")
    ex.add_argument("--input", type=Path, required=True, help="Raster source (GeoTIFF en coordonnées géographiques)")
    ex.add_argument("--output", type=Path, required=True, help="GeoTIFF compressé à écrire")
    ex.add_argument("--region", help="Emprise prédéfinie : france, haute-garonne")
    ex.add_argument("--bbox", type=float, nargs=4, metavar=("OUEST", "SUD", "EST", "NORD"), help="Emprise en degrés")
    ex.add_argument("--margin", type=float, default=0.05, help="Marge ajoutée à l'emprise, en degrés (défaut 0.05)")

    db = sub.add_parser("db", help="Gestion de la base PostgreSQL/PostGIS")
    db_sub = db.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("migrate", help="Applique les migrations de schéma manquantes")
    db_sub.add_parser("status", help="Affiche les migrations appliquées et en attente")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.command == "sample-data":
        from .sample_data import make_sample_data

        try:
            for path in make_sample_data(args.output, resolve_period(args.period)):
                print(f"{path} (données SYNTHÉTIQUES)")
        except ValueError as exc:
            print(f"Erreur : {exc}", file=sys.stderr)
            return 2
        return 0

    if args.command == "extract-raster":
        from .raster_extract import extract_window, resolve_bbox

        try:
            bbox = resolve_bbox(tuple(args.bbox) if args.bbox else None, args.region)
            result = extract_window(args.input, args.output, bbox, args.margin)
        except (ValueError, OSError, rasterio.errors.RasterioError) as exc:
            print(f"Erreur : {exc}", file=sys.stderr)
            return 2
        print(f"{result.path} : {result.width} x {result.height} pixels, {result.size_bytes / 1e6:.1f} Mo")
        return 0

    if args.command == "db":
        return _db_command(args.db_command)

    try:
        period = resolve_period(args.period)
        definition = load_chain_definition(args.config)
        components = default_registry().build(definition)
        listeners = _history_listeners()
    except (ValueError, OSError, SchemaOutdatedError, psycopg.Error) as exc:
        print(f"Erreur de configuration : {exc}", file=sys.stderr)
        return 2

    run = ChainExecutor(definition, components, args.workspace, listeners).run(period, trigger="cli")
    print(format_run(run))
    return 0 if run.status == Status.SUCCEEDED else 1


def _history_listeners() -> list:
    """Historique des exécutions en base si `LUCIOLES_DATABASE_URL` est définie."""
    try:
        database = Database(database_url())
    except ConfigurationError:
        return []
    database.ensure_current()
    return [PostgresRunListener(database)]


def _db_command(command: str) -> int:
    try:
        database = Database(database_url())
        if command == "migrate":
            applied = database.migrate()
            print(f"Migrations appliquées : {', '.join(applied)}" if applied else "Schéma déjà à jour")
        else:
            print(f"Appliquées : {', '.join(database.applied_versions()) or 'aucune'}")
            print(f"En attente : {', '.join(m.version for m in database.pending()) or 'aucune'}")
    except (ConfigurationError, psycopg.Error) as exc:
        print(f"Erreur de base de données : {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
