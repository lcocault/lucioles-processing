"""Doubles de test en mémoire pour chacun des ports de la chaîne."""

from lucioles_processing.application.registry import Components, Registry
from lucioles_processing.config import ChainDefinition, parse_chain_definition
from lucioles_processing.domain.model import (
    Dataset,
    FetchedFile,
    IndicatorValue,
    Observation,
    ProductFile,
    Territory,
)
from lucioles_processing.domain.ports import (
    DataFetcher,
    DataReader,
    IndicatorCalculator,
    IndicatorRepository,
    ProductBuilder,
    ProductDistributor,
    RunListener,
)
from lucioles_processing.domain.run import Step


class FakeFetcher(DataFetcher):
    def fetch(self, ctx):
        f = ctx.directory("raw") / "a.txt"
        f.write_text("a")
        return {"a": FetchedFile.local(f)}


class FakeReader(DataReader):
    def read(self, ctx, raw):
        return Dataset(
            ctx.period, (Territory("A"),), ("a",), (Observation("a", "A", 5.0),)
        )


class FakeCalculator(IndicatorCalculator):
    def calculate(self, ctx, dataset):
        return [IndicatorValue("ind", ctx.period, "A", 5.0, 0)]


class FakeRepository(IndicatorRepository):
    def __init__(self):
        self.saved = []

    def save(self, ctx, territories, values):
        self.saved.append((list(territories), list(values)))


class FakeBuilder(ProductBuilder):
    def build(self, ctx, dataset, values):
        f = ctx.directory("products") / "out.txt"
        f.write_text("x")
        return [ProductFile("out.txt", f, "txt")]


class FakeDistributor(ProductDistributor):
    def __init__(self):
        self.distributed = []

    def distribute(self, ctx, products):
        self.distributed.extend(products)


class Failing:
    """Mixin : remplace la méthode de l'étape par une erreur."""

    def __init__(self, method):
        setattr(self, method, self._boom)

    @staticmethod
    def _boom(*args, **kwargs):
        raise RuntimeError("boom")


class RecordingListener(RunListener):
    def __init__(self):
        self.snapshots = []

    def run_updated(self, run):
        self.snapshots.append((run.status, [(s.step, s.status) for s in run.steps]))


class BrokenListener(RunListener):
    def run_updated(self, run):
        raise RuntimeError("listener down")


def make_components(**overrides) -> Components:
    parts = {
        "fetcher": FakeFetcher(), "reader": FakeReader(), "calculator": FakeCalculator(),
        "repository": FakeRepository(), "builder": FakeBuilder(), "distributor": FakeDistributor(),
    }
    parts.update(overrides)
    return Components(**parts)


def raw_definition(**steps) -> dict:
    base = {
        "chain": "demo",
        "indicator": {"name": "ind", "weights": {"a": 1.0}, "thresholds": [1, 2, 3, 4]},
        "sources": {"a": {"method": "zonal_mean", "path": "a.tif"}},
        "boundaries": {"path": "communes.gpkg"},
        "steps": {
            "fetch": {"use": "fake"}, "read": {"use": "fake"},
            "calculate": {"use": "fake"}, "build": {"use": "fake"},
        },
    }
    base["steps"].update(steps)
    return base


def make_definition() -> ChainDefinition:
    return parse_chain_definition(raw_definition())


def fake_registry() -> Registry:
    reg = Registry()
    for step, factory in {
        Step.FETCH: FakeFetcher, Step.READ: FakeReader, Step.CALCULATE: FakeCalculator,
        Step.SAVE: FakeRepository, Step.BUILD: FakeBuilder, Step.DISTRIBUTE: FakeDistributor,
    }.items():
        reg.register(step, "fake", lambda ctx, f=factory: f())
    reg.register(Step.SAVE, "none", lambda ctx: FakeRepository())
    reg.register(Step.DISTRIBUTE, "none", lambda ctx: FakeDistributor())
    return reg
