import pytest

from lucioles_processing.adapters.postgres.database import (
    ConfigurationError,
    Database,
    database_url,
    list_migrations,
)
from lucioles_processing.adapters.registry import default_registry
from lucioles_processing.cli import main
from lucioles_processing.config import parse_chain_definition
from lucioles_processing.domain.run import Step
from tests.doubles import raw_definition


def test_database_url_from_environment():
    assert database_url({"LUCIOLES_DATABASE_URL": " postgresql://u@h/db "}) == "postgresql://u@h/db"


def test_database_url_custom_variable():
    assert database_url({"X": "postgresql://h/db"}, env_var="X") == "postgresql://h/db"


@pytest.mark.parametrize("environ", [{}, {"LUCIOLES_DATABASE_URL": ""}, {"LUCIOLES_DATABASE_URL": "  "}])
def test_database_url_missing(environ):
    with pytest.raises(ConfigurationError, match="LUCIOLES_DATABASE_URL"):
        database_url(environ)


def test_error_message_never_contains_the_secret():
    with pytest.raises(ConfigurationError) as err:
        Database.from_env({"OTHER": "postgresql://user:secret@h/db"})
    assert "secret" not in str(err.value)


def test_migrations_are_ordered_and_well_formed():
    migrations = list_migrations()
    assert migrations, "au moins une migration est fournie"
    versions = [m.version for m in migrations]
    assert versions == sorted(versions) == [f"{i:03d}" for i in range(1, len(versions) + 1)]
    assert "postgis" in migrations[0].sql.lower()
    assert all(m.sql.strip() for m in migrations)


def test_initial_migration_declares_expected_tables():
    sql = list_migrations()[0].sql
    for table in ("territory", "indicator", "indicator_value", "chain_run", "step_run"):
        assert f"CREATE TABLE {table} " in sql


def test_postgres_repository_is_registered_and_needs_the_variable(monkeypatch):
    monkeypatch.delenv("LUCIOLES_DATABASE_URL", raising=False)
    registry = default_registry()
    assert "postgres" in registry.names(Step.SAVE)
    definition = parse_chain_definition(
        raw_definition(
            fetch={"use": "configured_sources"},
            read={"use": "commune_aggregation", "params": {"admin": "x.gpkg"}},
            calculate={"use": "weighted_sum"},
            build={"use": "map_files"},
            save={"use": "postgres"},
        )
    )
    with pytest.raises(ValueError, match="LUCIOLES_DATABASE_URL"):
        registry.build(definition)
    monkeypatch.setenv("LUCIOLES_DATABASE_URL", "postgresql://u@h/db")
    assert registry.build(definition).repository.db.url == "postgresql://u@h/db"  # sans connexion


def test_cli_db_without_url_is_a_configuration_error(monkeypatch, capsys):
    monkeypatch.delenv("LUCIOLES_DATABASE_URL", raising=False)
    assert main(["db", "migrate"]) == 2
    assert "LUCIOLES_DATABASE_URL" in capsys.readouterr().err


def test_cli_db_with_unreachable_server_is_an_error(monkeypatch, capsys):
    monkeypatch.setenv("LUCIOLES_DATABASE_URL", "postgresql://u:p@127.0.0.1:1/db?connect_timeout=1")
    assert main(["db", "status"]) == 2
    assert "Erreur de base de données" in capsys.readouterr().err
