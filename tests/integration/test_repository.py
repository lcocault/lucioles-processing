import pytest

from lucioles_processing.adapters.postgres.database import SchemaOutdatedError
from lucioles_processing.adapters.postgres.repository import PostgresIndicatorRepository
from lucioles_processing.domain.model import IndicatorValue, Period, Territory
from lucioles_processing.domain.ports import StepContext

pytestmark = pytest.mark.integration

P9, P10 = Period(2026, 9), Period(2026, 10)
SQUARE = "POLYGON((1 43, 1.1 43, 1.1 43.1, 1 43.1, 1 43))"
TERRITORIES = [
    Territory("A", "Commune A", "31", SQUARE),
    Territory("B", "Commune B", "31", None),
]


def ctx(period=P10, tmp_path=None):
    return StepContext("run", "chain", period, tmp_path)


def values(period=P10, a=(12.0, 1), b=(None, None)):
    return [
        IndicatorValue("air", period, "A", *a),
        IndicatorValue("air", period, "B", *b),
    ]


@pytest.fixture
def repo(db):
    return PostgresIndicatorRepository(db)


def test_save_and_find_round_trip(repo):
    repo.save(ctx(), TERRITORIES, values())
    assert repo.find("air", P10) == values()
    assert repo.find("air", P10, "A") == values()[:1]
    assert repo.find("air", P9) == []
    assert repo.find("other", P10) == []


def test_territories_are_stored_with_their_geometry(repo, db):
    repo.save(ctx(), TERRITORIES, values())
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT code, name, department, ST_AsText(geometry), ST_SRID(geometry) FROM territory ORDER BY code"
        ).fetchall()
    assert rows[0] == ("A", "Commune A", "31", "POLYGON((1 43,1.1 43,1.1 43.1,1 43.1,1 43))", 4326)
    assert rows[1][3] is None


def test_save_is_idempotent_and_replaces_values(repo, db):
    repo.save(ctx(), TERRITORIES, values())
    repo.save(ctx(), TERRITORIES, values(a=(50.0, 4), b=(5.0, 0)))
    assert repo.find("air", P10) == values(a=(50.0, 4), b=(5.0, 0))
    with db.connect() as conn:
        assert conn.execute("SELECT count(*) FROM indicator_value").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM territory").fetchone()[0] == 2


def test_rerun_removes_territories_no_longer_computed(repo):
    repo.save(ctx(), TERRITORIES, values())
    repo.save(ctx(), TERRITORIES[:1], values()[:1])
    assert [v.territory_code for v in repo.find("air", P10)] == ["A"]


def test_other_periods_are_kept(repo):
    repo.save(ctx(P9), TERRITORIES, values(P9, a=(1.0, 0), b=(1.0, 0)))
    repo.save(ctx(), TERRITORIES, values())
    assert len(repo.find("air", P9)) == 2 and len(repo.find("air", P10)) == 2


def test_failure_rolls_everything_back(repo, db):
    bad = values() + [IndicatorValue("air", P10, "UNKNOWN", 1.0, 0)]  # territoire inconnu : clé étrangère
    with pytest.raises(Exception, match="foreign key|violates"):
        repo.save(ctx(), TERRITORIES, bad)
    with db.connect() as conn:
        assert conn.execute("SELECT count(*) FROM territory").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM indicator_value").fetchone()[0] == 0


def test_failure_keeps_previous_values(repo):
    repo.save(ctx(), TERRITORIES, values())
    bad = values(a=(99.0, 4)) + [IndicatorValue("air", P10, "UNKNOWN", 1.0, 0)]
    with pytest.raises(Exception, match="violates"):
        repo.save(ctx(), TERRITORIES, bad)
    assert repo.find("air", P10) == values()


def test_save_requires_a_current_schema(empty_db):
    with pytest.raises(SchemaOutdatedError):
        PostgresIndicatorRepository(empty_db).save(ctx(), TERRITORIES, values())
