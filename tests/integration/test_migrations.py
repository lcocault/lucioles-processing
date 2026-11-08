import psycopg
import pytest

from lucioles_processing.adapters.postgres.database import SchemaOutdatedError, list_migrations

pytestmark = pytest.mark.integration


def tables(db):
    with db.connect() as conn:
        rows = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        return {r[0] for r in rows}


def test_migrate_creates_schema_on_empty_database(empty_db):
    applied = empty_db.migrate()
    assert applied == [m.version for m in list_migrations()]
    assert {"territory", "indicator", "indicator_value", "chain_run", "step_run", "schema_migration"} <= tables(empty_db)
    assert empty_db.pending() == []


def test_postgis_is_enabled(db):
    with db.connect() as conn:
        assert conn.execute("SELECT PostGIS_Version()").fetchone()[0]


def test_migrate_twice_is_a_no_op(empty_db):
    empty_db.migrate()
    assert empty_db.migrate() == []
    assert empty_db.applied_versions() == [m.version for m in list_migrations()]


def test_ensure_current(empty_db):
    with pytest.raises(SchemaOutdatedError, match="lucioles db migrate"):
        empty_db.ensure_current()
    empty_db.migrate()
    empty_db.ensure_current()


def test_constraints_reject_inconsistent_rows(db):
    with db.connect() as conn:
        conn.execute("INSERT INTO territory (code) VALUES ('A')")
        conn.execute("INSERT INTO indicator (name) VALUES ('i')")
    insert = "INSERT INTO indicator_value VALUES ('i', %s, 'A', %s, %s)"
    for args in [("2026-10-02", 1.0, 1), ("2026-10-01", 1.0, 7), ("2026-10-01", None, 1), ("2026-10-01", 1.0, None)]:
        with pytest.raises(psycopg.errors.CheckViolation), db.connect() as conn:
            conn.execute(insert, args)


def test_view_joins_geometry(db):
    with db.connect() as conn:
        conn.execute("INSERT INTO territory VALUES ('A', 'Commune A', '31', ST_GeomFromText('POINT(1 43)', 4326))")
        conn.execute("INSERT INTO indicator VALUES ('i')")
        conn.execute("INSERT INTO indicator_value VALUES ('i', '2026-10-01', 'A', 12.0, 1)")
        row = conn.execute("SELECT territory_name, ST_AsText(geometry) FROM indicator_map").fetchone()
    assert row == ("Commune A", "POINT(1 43)")
