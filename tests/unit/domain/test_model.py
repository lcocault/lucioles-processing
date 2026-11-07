from pathlib import Path

import pytest

from lucioles_processing.domain.model import (
    Dataset,
    IndicatorValue,
    Observation,
    Period,
    ProductFile,
    Territory,
)


class TestPeriod:
    def test_parse_and_str(self):
        period = Period.parse("2026-03")
        assert (period.year, period.month) == (2026, 3)
        assert str(period) == "2026-03"

    def test_fields(self):
        assert Period(2026, 3).fields() == {"period": "2026-03", "year": "2026", "month": "03"}

    @pytest.mark.parametrize("text", ["2026", "2026-13", "2026-00", "26-10", "2026/10", "abcd-ef", ""])
    def test_invalid_text(self, text):
        with pytest.raises(ValueError, match="Période invalide"):
            Period.parse(text)

    def test_invalid_numbers(self):
        with pytest.raises(ValueError):
            Period(2026, 13)

    def test_ordering_and_immutability(self):
        assert Period(2025, 12) < Period(2026, 1)
        with pytest.raises(AttributeError):
            Period(2026, 1).year = 2000


class TestTerritory:
    def test_requires_code(self):
        with pytest.raises(ValueError, match="code"):
            Territory(code="")


class TestDataset:
    def make(self, **kw):
        args = {
            "period": Period(2026, 10),
            "territories": (Territory("A"), Territory("B")),
            "sources": ("no2",),
            "observations": (Observation("no2", "A", 12.0), Observation("no2", "B", None)),
        }
        args.update(kw)
        return Dataset(**args)

    def test_value_lookup(self):
        ds = self.make()
        assert ds.value("no2", "A") == 12.0
        assert ds.value("no2", "B") is None
        assert ds.value("pm10", "A") is None

    def test_rejects_duplicate_territories(self):
        with pytest.raises(ValueError, match="double"):
            self.make(territories=(Territory("A"), Territory("A")))

    def test_rejects_unknown_territory(self):
        with pytest.raises(ValueError, match="territoire inconnu"):
            self.make(observations=(Observation("no2", "Z", 1.0),))

    def test_rejects_unknown_source(self):
        with pytest.raises(ValueError, match="source inconnue"):
            self.make(observations=(Observation("pm10", "A", 1.0),))


class TestIndicatorValue:
    def test_valid(self):
        v = IndicatorValue("air", Period(2026, 10), "A", 12.5, 1)
        assert v.level == 1

    def test_missing_value_has_no_level(self):
        assert IndicatorValue("air", Period(2026, 10), "A", None, None).level is None

    @pytest.mark.parametrize("level", [-1, 5])
    def test_level_out_of_range(self, level):
        with pytest.raises(ValueError, match="Niveau"):
            IndicatorValue("air", Period(2026, 10), "A", 1.0, level)

    def test_level_without_value(self):
        with pytest.raises(ValueError):
            IndicatorValue("air", Period(2026, 10), "A", None, 2)

    def test_value_without_level(self):
        with pytest.raises(ValueError):
            IndicatorValue("air", Period(2026, 10), "A", 1.0, None)


def test_product_file():
    assert ProductFile("a.kml", Path("a.kml"), "kml").format == "kml"
