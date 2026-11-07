from lucioles_processing.application.executor import ChainExecutor
from lucioles_processing.domain.model import Period
from lucioles_processing.domain.run import Status, Step
from tests.doubles import (
    BrokenListener,
    Failing,
    FakeBuilder,
    FakeCalculator,
    FakeDistributor,
    FakeFetcher,
    FakeRepository,
    RecordingListener,
    make_components,
    make_definition,
)

PERIOD = Period(2026, 10)


def executor(tmp_path, listeners=None, **overrides):
    return ChainExecutor(make_definition(), make_components(**overrides), tmp_path, listeners)


def test_successful_run(tmp_path):
    repo, dist = FakeRepository(), FakeDistributor()
    run = executor(tmp_path, repository=repo, distributor=dist).run(PERIOD)
    assert run.status == Status.SUCCEEDED
    assert [s.status for s in run.steps] == [Status.SUCCEEDED] * 6
    assert all(s.duration is not None for s in run.steps)
    assert run.duration is not None and run.error is None
    assert len(repo.saved[0]) == 1
    assert [p.name for p in dist.distributed] == ["out.txt"]
    assert [p.name for p in run.products] == ["out.txt"]


def test_workspace_is_dedicated_to_the_run(tmp_path):
    ex = executor(tmp_path)
    first, second = ex.run(PERIOD), ex.run(PERIOD)
    assert first.id != second.id
    assert (tmp_path / "demo" / "2026-10" / first.id / "raw" / "a.txt").exists()
    assert (tmp_path / "demo" / "2026-10" / second.id / "products" / "out.txt").exists()


def test_run_records_trigger_and_implementations(tmp_path):
    run = executor(tmp_path).run(PERIOD, trigger="api")
    assert run.trigger == "api"
    assert run.step(Step.FETCH).implementation == "fake"
    assert run.chain == "demo" and run.period == PERIOD


def test_failure_stops_chain_and_skips_next_steps(tmp_path):
    repo, dist = FakeRepository(), FakeDistributor()
    run = executor(
        tmp_path, calculator=_failing(FakeCalculator(), "calculate"), repository=repo, distributor=dist
    ).run(PERIOD)
    statuses = {s.step: s.status for s in run.steps}
    assert statuses == {
        Step.FETCH: Status.SUCCEEDED, Step.READ: Status.SUCCEEDED, Step.CALCULATE: Status.FAILED,
        Step.SAVE: Status.SKIPPED, Step.BUILD: Status.SKIPPED, Step.DISTRIBUTE: Status.SKIPPED,
    }
    assert run.status == Status.FAILED
    assert run.error == "RuntimeError: boom"
    assert run.step(Step.CALCULATE).error == "RuntimeError: boom"
    assert repo.saved == [] and dist.distributed == []
    assert run.step(Step.SAVE).started_at is None


def test_failure_on_first_step(tmp_path):
    run = executor(tmp_path, fetcher=_failing(FakeFetcher(), "fetch")).run(PERIOD)
    assert run.step(Step.FETCH).status == Status.FAILED
    assert all(s.status == Status.SKIPPED for s in run.steps[1:])


def test_failure_on_last_step(tmp_path):
    run = executor(tmp_path, distributor=_failing(FakeDistributor(), "distribute")).run(PERIOD)
    assert run.status == Status.FAILED
    assert run.step(Step.BUILD).status == Status.SUCCEEDED
    assert run.step(Step.DISTRIBUTE).status == Status.FAILED


def test_listener_receives_progress(tmp_path):
    listener = RecordingListener()
    executor(tmp_path, [listener]).run(PERIOD)
    statuses = [s for s, _ in listener.snapshots]
    assert statuses[0] == Status.RUNNING and statuses[-1] == Status.SUCCEEDED
    assert len(listener.snapshots) == 1 + 6 * 2 + 1  # début + (début, fin) par étape + fin
    # les étapes passent par `running` avant de réussir
    assert any(steps[0] == (Step.FETCH, Status.RUNNING) for _, steps in listener.snapshots)


def test_broken_listener_does_not_break_the_chain(tmp_path):
    good = RecordingListener()
    run = executor(tmp_path, [BrokenListener(), good]).run(PERIOD)
    assert run.status == Status.SUCCEEDED
    assert good.snapshots


def test_default_builder_is_used(tmp_path):
    assert isinstance(make_components().builder, FakeBuilder)


def _failing(component, method):
    component.__dict__[method] = Failing._boom
    return component
