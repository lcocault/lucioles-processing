"""Parcours complet avec enregistrement PostgreSQL/PostGIS et historique (nécessite une base de test)."""

import pandas as pd
import pytest

from lucioles_processing.adapters.postgres.repository import PostgresIndicatorRepository
from lucioles_processing.adapters.postgres.run_history import PostgresRunStore
from lucioles_processing.cli import main
from lucioles_processing.domain.model import Period
from lucioles_processing.domain.run import Step

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

CHAIN = """
chain: air
indicator: {{name: air, weights: {{pm10: 1.0}}, thresholds: [10, 20, 30, 40]}}
boundaries:
  path: {admin}
sources:
  pm10:
    method: nearest_station
    path: {data}/pm10_{{period}}.csv
    field: pm10
    dims: [lon, lat]
steps:
  fetch: {{use: configured_sources}}
  read: {{use: commune_aggregation}}
  calculate: {{use: weighted_sum}}
  save: {{use: postgres}}
  build:
    use: map_files
    params: {{formats: [geojson]}}
"""


@pytest.fixture
def env(communes, db, tmp_path, monkeypatch):
    admin = tmp_path / "admin.gpkg"
    communes.to_file(admin, driver="GPKG")
    pd.DataFrame({"lon": [1.05, 1.25], "lat": [43.05, 43.25], "pm10": [5.0, 45.0]}).to_csv(
        tmp_path / "pm10_2026-10.csv", sep=";", index=False
    )
    cfg = tmp_path / "chain.yaml"
    cfg.write_text(CHAIN.format(data=tmp_path, admin=admin))
    monkeypatch.setenv("LUCIOLES_DATABASE_URL", db.url)
    return cfg, tmp_path


def run_cli(cfg, tmp_path):
    return main(["run", "--config", str(cfg), "--period", "2026-10", "--workspace", str(tmp_path / "ws")])


def test_chain_saves_indicators_and_history(env, db):
    cfg, tmp_path = env
    assert run_cli(cfg, tmp_path) == 0
    repo = PostgresIndicatorRepository(db)
    found = repo.find("air", Period(2026, 10))
    assert [(v.value, v.level) for v in found] == [(5.0, 0), (45.0, 4)]
    with db.connect() as conn:
        assert conn.execute("SELECT count(*) FROM territory WHERE geometry IS NOT NULL").fetchone()[0] == 2
        run_id, status = conn.execute("SELECT id, status FROM chain_run").fetchone()
    assert status == "succeeded"
    assert PostgresRunStore(db).get(run_id).step(Step.SAVE).status.value == "succeeded"


def test_rerun_does_not_duplicate(env, db):
    cfg, tmp_path = env
    assert run_cli(cfg, tmp_path) == 0
    assert run_cli(cfg, tmp_path) == 0
    with db.connect() as conn:
        assert conn.execute("SELECT count(*) FROM indicator_value").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM chain_run").fetchone()[0] == 2  # deux exécutions tracées


def test_failure_is_recorded_in_history(env, db):
    cfg, tmp_path = env
    (tmp_path / "pm10_2026-10.csv").unlink()
    assert run_cli(cfg, tmp_path) == 1
    with db.connect() as conn:
        assert conn.execute("SELECT status FROM chain_run").fetchone()[0] == "failed"
        assert conn.execute("SELECT count(*) FROM indicator_value").fetchone()[0] == 0


def test_run_requires_migrated_schema(env, empty_db_factory, monkeypatch, capsys):
    cfg, tmp_path = env
    monkeypatch.setenv("LUCIOLES_DATABASE_URL", empty_db_factory().url)
    assert run_cli(cfg, tmp_path) == 2
    assert "lucioles db migrate" in capsys.readouterr().err
