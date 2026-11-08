import pytest

from lucioles_processing.adapters.postgres.run_history import (
    INTERRUPTED,
    PostgresRunListener,
    PostgresRunStore,
)
from lucioles_processing.application.executor import ChainExecutor
from lucioles_processing.domain.model import Period
from lucioles_processing.domain.run import ChainRun, Status, Step, StepRun
from tests.doubles import Failing, FakeCalculator, make_components, make_definition

pytestmark = pytest.mark.integration

PERIOD = Period(2026, 10)


def execute(db, tmp_path, **overrides):
    executor = ChainExecutor(
        make_definition(), make_components(**overrides), tmp_path, [PostgresRunListener(db)]
    )
    return executor.run(PERIOD, trigger="api")


def test_successful_run_is_recorded(db, tmp_path):
    run = execute(db, tmp_path)
    stored = PostgresRunStore(db).get(run.id)
    assert stored.status == Status.SUCCEEDED
    assert (stored.chain, stored.period, stored.trigger) == ("demo", PERIOD, "api")
    assert [s.step for s in stored.steps] == list(Step)
    assert all(s.status == Status.SUCCEEDED and s.duration is not None for s in stored.steps)
    assert stored.steps[0].implementation == "fake"


def test_failed_run_keeps_error_and_skipped_steps(db, tmp_path):
    calc = FakeCalculator()
    calc.__dict__["calculate"] = Failing._boom
    run = execute(db, tmp_path, calculator=calc)
    stored = PostgresRunStore(db).get(run.id)
    assert stored.status == Status.FAILED
    assert stored.error == "RuntimeError: boom"
    assert [s.status for s in stored.steps] == [
        Status.SUCCEEDED, Status.SUCCEEDED, Status.FAILED, Status.SKIPPED, Status.SKIPPED, Status.SKIPPED
    ]


def test_runs_are_not_mixed_up(db, tmp_path):
    first, second = execute(db, tmp_path), execute(db, tmp_path)
    store = PostgresRunStore(db)
    assert store.get(first.id).id != store.get(second.id).id
    assert store.get("absent") is None


def _stuck_run(db, status, step_statuses):
    run = ChainRun("demo", PERIOD, [StepRun(s, "fake", st) for s, st in zip(Step, step_statuses, strict=True)],
                   status=status)
    PostgresRunListener(db).run_updated(run)
    return run


def test_recover_interrupted_runs(db):
    S, R, P = Status.SUCCEEDED, Status.RUNNING, Status.PENDING
    stuck = _stuck_run(db, Status.RUNNING, [S, R, P, P, P, P])
    queued = _stuck_run(db, Status.PENDING, [P] * 6)
    done = _stuck_run(db, Status.SUCCEEDED, [S] * 6)
    store = PostgresRunStore(db)

    assert store.recover_interrupted() == 2

    recovered = store.get(stuck.id)
    assert recovered.status == Status.FAILED and recovered.error == INTERRUPTED
    assert [s.status for s in recovered.steps] == [S, Status.FAILED, *[Status.SKIPPED] * 4]
    assert recovered.finished_at is not None
    assert store.get(queued.id).status == Status.FAILED
    assert store.get(done.id).status == Status.SUCCEEDED
    assert store.recover_interrupted() == 0
