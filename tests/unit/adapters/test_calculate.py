import pytest

from lucioles_processing.adapters.calculate import WeightedSumCalculator
from lucioles_processing.config import IndicatorSpec
from lucioles_processing.domain.model import Dataset, Observation, Period, Territory
from lucioles_processing.domain.ports import StepContext

PERIOD = Period(2026, 10)
CTX = StepContext("r", "c", PERIOD, workspace=None)
SPEC = IndicatorSpec("ind", {"a": 0.5, "b": 0.5}, [10, 20, 30, 40])


def dataset(*rows):
    """rows : (code, valeur a, valeur b)"""
    return Dataset(
        PERIOD,
        tuple(Territory(code) for code, _, _ in rows),
        ("a", "b"),
        tuple(o for code, a, b in rows for o in (Observation("a", code, a), Observation("b", code, b))),
    )


def levels(*rows):
    return [v.level for v in WeightedSumCalculator(SPEC).calculate(CTX, dataset(*rows))]


def test_weighted_sum_value():
    [v] = WeightedSumCalculator(SPEC).calculate(CTX, dataset(("X", 10.0, 30.0)))
    assert v.value == 20.0 and v.level == 2
    assert (v.indicator, v.period, v.territory_code) == ("ind", PERIOD, "X")


@pytest.mark.parametrize(
    "value,level", [(0, 0), (9.9, 0), (10, 1), (19.99, 1), (20, 2), (35, 3), (40, 4), (100, 4)]
)
def test_levels(value, level):
    assert levels(("X", value, value)) == [level]


def test_missing_data_is_not_zero():
    assert levels(("X", 5.0, None), ("Y", None, None)) == [None, None]


def test_missing_on_unweighted_source_is_ignored():
    spec = IndicatorSpec("ind", {"a": 1.0}, [10, 20, 30, 40])
    [v] = WeightedSumCalculator(spec).calculate(CTX, dataset(("X", 15.0, None)))
    assert v.level == 1


def test_one_value_per_territory_in_order():
    values = WeightedSumCalculator(SPEC).calculate(CTX, dataset(("B", 1.0, 1.0), ("A", 50.0, 50.0)))
    assert [v.territory_code for v in values] == ["B", "A"]
