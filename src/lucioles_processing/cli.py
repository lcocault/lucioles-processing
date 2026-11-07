"""Interface en ligne de commande : `lucioles run ...`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lucioles", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="Exécute une chaîne de traitement pour une période")
    p.add_argument("--config", type=Path, required=True, help="Définition YAML de la chaîne")
    p.add_argument("--period", required=True, help="Période AAAA-MM")
    p.add_argument("--workspace", type=Path, default=Path("workspace"), help="Racine des espaces de travail")
    p.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        period = Period.parse(args.period)
        definition = load_chain_definition(args.config)
        components = default_registry().build(definition)
    except (ValueError, OSError) as exc:
        print(f"Erreur de configuration : {exc}", file=sys.stderr)
        return 2

    run = ChainExecutor(definition, components, args.workspace).run(period, trigger="cli")
    print(format_run(run))
    return 0 if run.status == Status.SUCCEEDED else 1


if __name__ == "__main__":
    sys.exit(main())
