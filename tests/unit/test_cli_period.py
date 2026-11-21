from datetime import date

import pytest

from lucioles_processing.cli import resolve_period
from lucioles_processing.domain.model import Period


def test_explicit_period():
    assert resolve_period("2026-03") == Period(2026, 3)


def test_previous_and_current_month():
    today = date(2026, 1, 5)
    assert resolve_period("previous-month", today) == Period(2025, 12)
    assert resolve_period("current-month", today) == Period(2026, 1)


def test_defaults_to_the_real_date():
    assert resolve_period("current-month") == Period.of_month(date.today())


def test_invalid():
    with pytest.raises(ValueError, match="Période invalide"):
        resolve_period("le-mois-dernier")


def test_annual_period_and_previous_year():
    today = date(2026, 1, 5)
    assert resolve_period("2023") == Period(2023)
    assert resolve_period("previous-year", today) == Period(2025)
    assert resolve_period("current-year", today) == Period(2026)
