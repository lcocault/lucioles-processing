from datetime import datetime, timedelta, timezone

from lucioles_processing.domain.model import Period
from lucioles_processing.domain.run import ChainRun, Status, Step, StepRun


def make_run():
    return ChainRun("air", Period(2026, 10), [StepRun(s, "impl") for s in Step])


def test_steps_are_in_chain_order():
    assert [s.value for s in Step] == ["fetch", "read", "calculate", "save", "build", "distribute"]


def test_new_run_is_pending_with_unique_id():
    a, b = make_run(), make_run()
    assert a.status == Status.PENDING and a.id != b.id
    assert all(s.status == Status.PENDING for s in a.steps)


def test_step_lookup():
    assert make_run().step(Step.BUILD).step == Step.BUILD


def test_durations():
    run = make_run()
    assert run.duration is None
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    run.started_at, run.finished_at = start, start + timedelta(seconds=3)
    assert run.duration == 3.0
    step = run.steps[0]
    assert step.duration is None
    step.started_at, step.finished_at = start, start + timedelta(seconds=1.5)
    assert step.duration == 1.5


def test_error_is_first_failed_step():
    run = make_run()
    assert run.error is None
    run.step(Step.READ).status, run.step(Step.READ).error = Status.FAILED, "boom"
    assert run.error == "boom"
