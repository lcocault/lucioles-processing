"""Interface en ligne de commande : `lucioles run ...`."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .pipeline import FORMATS, run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="lucioles", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="Calcule un indicateur pour une période")
    p.add_argument("--config", type=Path, required=True, help="Fichier YAML de l'indicateur")
    p.add_argument("--period", required=True, help="Période AAAA-MM")
    p.add_argument("--admin", type=Path, required=True, help="GeoPackage ADMIN_EXPRESS")
    p.add_argument("--output", type=Path, default=Path("output"))
    p.add_argument("--cache", type=Path, default=Path("cache"))
    p.add_argument("--formats", nargs="+", choices=FORMATS, default=list(FORMATS))
    p.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run(args.config, args.period, args.admin, args.output, args.cache, tuple(args.formats))


if __name__ == "__main__":
    main()
