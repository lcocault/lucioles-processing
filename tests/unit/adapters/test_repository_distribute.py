from lucioles_processing.adapters.distribute import LocalFolderDistributor, NullDistributor
from lucioles_processing.adapters.repository import InMemoryRepository, NullRepository
from lucioles_processing.domain.model import IndicatorValue, Period, ProductFile
from lucioles_processing.domain.ports import StepContext

P1, P2 = Period(2026, 9), Period(2026, 10)


def ctx(tmp_path, period=P2):
    return StepContext("r", "chain", period, tmp_path)


def test_in_memory_repository_is_idempotent(tmp_path):
    repo = InMemoryRepository()
    v1 = [IndicatorValue("i", P2, "A", 1.0, 0)]
    v2 = [IndicatorValue("i", P2, "A", 50.0, 4), IndicatorValue("i", P2, "B", 2.0, 0)]
    repo.save(ctx(tmp_path), v1)
    repo.save(ctx(tmp_path), v2)
    assert repo.store[("i", P2)] == v2


def test_in_memory_repository_keeps_other_periods(tmp_path):
    repo = InMemoryRepository()
    repo.save(ctx(tmp_path, P1), [IndicatorValue("i", P1, "A", 1.0, 0)])
    repo.save(ctx(tmp_path), [IndicatorValue("i", P2, "A", 2.0, 0)])
    assert set(repo.store) == {("i", P1), ("i", P2)}


def test_null_repository(tmp_path):
    assert NullRepository().save(ctx(tmp_path), []) is None


def test_local_folder_distributor_copies_and_overwrites(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    f = src / "a.kml"
    f.write_text("v1")
    product = ProductFile("a.kml", f, "kml")
    dist = LocalFolderDistributor(tmp_path / "out")
    dist.distribute(ctx(tmp_path), [product])
    f.write_text("v2")
    dist.distribute(ctx(tmp_path), [product])
    assert (tmp_path / "out" / "chain" / "2026-10" / "a.kml").read_text() == "v2"


def test_null_distributor(tmp_path):
    assert NullDistributor().distribute(ctx(tmp_path), []) is None
