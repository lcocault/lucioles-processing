"""État d'exécution d'une chaîne de traitement."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .model import Period, ProductFile


class Step(str, Enum):
    """Les six étapes d'une chaîne, dans l'ordre d'exécution."""

    FETCH = "fetch"
    READ = "read"
    CALCULATE = "calculate"
    SAVE = "save"
    BUILD = "build"
    DISTRIBUTE = "distribute"


class Status(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"  # étape non exécutée car une étape précédente a échoué


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class StepRun:
    step: Step
    implementation: str
    status: Status = Status.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None

    @property
    def duration(self) -> float | None:
        """Durée en secondes ; `None` tant que l'étape n'est pas terminée."""
        if self.started_at is None or self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()


@dataclass
class ChainRun:
    """Une exécution d'une chaîne pour une période. Mutable : seul l'exécuteur la modifie."""

    chain: str
    period: Period
    steps: list[StepRun]
    trigger: str = "cli"  # cli | api | schedule
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: Status = Status.PENDING
    created_at: datetime = field(default_factory=_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    products: list[ProductFile] = field(default_factory=list)

    def step(self, step: Step) -> StepRun:
        return next(s for s in self.steps if s.step == step)

    @property
    def duration(self) -> float | None:
        if self.started_at is None or self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def error(self) -> str | None:
        """Erreur de la première étape en échec."""
        return next((s.error for s in self.steps if s.status == Status.FAILED), None)
