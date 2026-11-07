"""Exécuteur de chaîne : enchaîne les six étapes dans un espace de travail dédié."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from ..config import ChainDefinition
from ..domain.model import Period
from ..domain.ports import RunListener, StepContext
from ..domain.run import ChainRun, Status, Step, StepRun
from .registry import Components

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChainExecutor:
    def __init__(
        self,
        definition: ChainDefinition,
        components: Components,
        workspace_root: Path,
        listeners: list[RunListener] | None = None,
    ):
        self.definition = definition
        self.components = components
        self.workspace_root = Path(workspace_root)
        self.listeners = list(listeners or [])

    def run(self, period: Period, trigger: str = "cli") -> ChainRun:
        """Exécute la chaîne. Une étape en échec arrête la chaîne ; l'erreur est portée par le résultat."""
        run = ChainRun(
            chain=self.definition.name,
            period=period,
            trigger=trigger,
            steps=[StepRun(s, self.definition.steps[s].use) for s in Step],
        )
        workspace = self.workspace_root / run.chain / str(period) / run.id
        workspace.mkdir(parents=True, exist_ok=True)
        ctx = StepContext(run.id, run.chain, period, workspace)

        run.status, run.started_at = Status.RUNNING, _now()
        self._notify(run)

        state: dict = {}
        failed = False
        for step_run in run.steps:
            if failed:
                step_run.status = Status.SKIPPED
                self._notify(run)
                continue
            step_run.status, step_run.started_at = Status.RUNNING, _now()
            self._notify(run)
            try:
                self._actions(run, ctx, state)[step_run.step]()
            except Exception as exc:
                log.exception("[%s] étape '%s' en échec", run.chain, step_run.step.value)
                step_run.status, step_run.error = Status.FAILED, f"{type(exc).__name__}: {exc}"
                failed = True
            else:
                step_run.status = Status.SUCCEEDED
            step_run.finished_at = _now()
            self._notify(run)

        run.status = Status.FAILED if failed else Status.SUCCEEDED
        run.finished_at = _now()
        self._notify(run)
        return run

    def _actions(self, run: ChainRun, ctx: StepContext, state: dict) -> dict[Step, Callable[[], None]]:
        c = self.components

        def fetch() -> None:
            state["raw"] = c.fetcher.fetch(ctx)

        def read() -> None:
            state["dataset"] = c.reader.read(ctx, state["raw"])

        def calculate() -> None:
            state["values"] = list(c.calculator.calculate(ctx, state["dataset"]))

        def save() -> None:
            c.repository.save(ctx, state["values"])

        def build() -> None:
            run.products = list(c.builder.build(ctx, state["dataset"], state["values"]))

        def distribute() -> None:
            c.distributor.distribute(ctx, run.products)

        return {
            Step.FETCH: fetch, Step.READ: read, Step.CALCULATE: calculate,
            Step.SAVE: save, Step.BUILD: build, Step.DISTRIBUTE: distribute,
        }

    def _notify(self, run: ChainRun) -> None:
        for listener in self.listeners:
            try:
                listener.run_updated(run)
            except Exception:
                log.exception("Écouteur d'exécution en erreur : %s", type(listener).__name__)
