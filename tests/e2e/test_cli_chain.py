"""Parcours complets : définition YAML -> CLI -> fichiers distribués, avec données synthétiques."""

import json

import geopandas as gpd
import pandas as pd
import pytest

from lucioles_processing.cli import main

pytestmark = pytest.mark.e2e

CHAIN = """
chain: air
indicator: {{name: air, weights: {{pm10: 1.0}}, thresholds: [10, 20, 30, 40]}}
boundaries:
  url: {url}/communes.geojson
  code_field: code_insee
  name_field: nom_officiel
  department_field: code_insee_du_departement
  departments: ["31"]
sources:
  pm10:
    method: nearest_station
    path: {data}/pm10_{{period}}.csv
    field: pm10
    dims: [lon, lat]
steps:
  fetch:
    use: configured_sources
    params: {{cache_dir: {cache}}}
  read: {{use: commune_aggregation}}
  calculate: {{use: weighted_sum}}
  build:
    use: map_files
    params: {{formats: [gpkg, geojson, kml]}}
  distribute:
    use: local_folder
    params: {{directory: {out}}}
"""


@pytest.fixture
def env(communes, tmp_path, http_server):
    http_server.files["/communes.geojson"] = communes.to_json().encode()
    pd.DataFrame({"lon": [1.05, 1.25], "lat": [43.05, 43.25], "pm10": [5.0, 45.0]}).to_csv(
        tmp_path / "pm10_2026-10.csv", sep=";", index=False
    )
    cfg = tmp_path / "chain.yaml"
    cfg.write_text(CHAIN.format(data=tmp_path, url=http_server.base_url, cache=tmp_path / "cache", out=tmp_path / "out"))
    return tmp_path, cfg


def run_cli(cfg, tmp_path, period="2026-10"):
    return main(["run", "--config", str(cfg), "--period", period, "--workspace", str(tmp_path / "ws")])


def test_nominal_run_distributes_files(env, capsys):
    tmp_path, cfg = env
    assert run_cli(cfg, tmp_path) == 0
    out = tmp_path / "out" / "air" / "2026-10"
    assert sorted(p.name for p in out.iterdir()) == ["air.geojson", "air.gpkg", "air.kml", "manifest.json"]
    gdf = gpd.read_file(out / "air.gpkg")
    assert gdf["opf_level"].tolist() == [0, 4]
    assert json.loads((out / "manifest.json").read_text())["missing"] == 0
    printed = capsys.readouterr().out
    assert "OK" in printed and "ÉCHEC" not in printed
    for step in ("fetch", "read", "calculate", "save", "build", "distribute"):
        assert step in printed


def test_rerun_overwrites_distribution(env):
    tmp_path, cfg = env
    assert run_cli(cfg, tmp_path) == 0
    assert run_cli(cfg, tmp_path) == 0
    assert len(list((tmp_path / "out" / "air" / "2026-10").iterdir())) == 4
    assert len(list((tmp_path / "ws" / "air" / "2026-10").iterdir())) == 2  # un espace par exécution


def test_missing_source_fails_with_step_status(env, capsys):
    tmp_path, cfg = env
    (tmp_path / "pm10_2026-10.csv").unlink()
    assert run_cli(cfg, tmp_path) == 1
    printed = capsys.readouterr().out
    assert "ÉCHEC" in printed and "FileNotFoundError" in printed
    assert printed.count("ignorée") == 5
    assert not (tmp_path / "out").exists()


def test_invalid_period_is_a_configuration_error(env, capsys):
    tmp_path, cfg = env
    assert run_cli(cfg, tmp_path, period="2026-13") == 2
    assert "Période invalide" in capsys.readouterr().err


def test_unknown_implementation_is_a_configuration_error(env, capsys):
    tmp_path, cfg = env
    cfg.write_text(cfg.read_text().replace("weighted_sum", "magie"))
    assert run_cli(cfg, tmp_path) == 2
    assert "magie" in capsys.readouterr().err


def test_missing_required_param_is_a_configuration_error(env, capsys):
    tmp_path, cfg = env
    cfg.write_text(cfg.read_text().replace("directory:", "dossier:"))
    assert run_cli(cfg, tmp_path) == 2
    assert "paramètre 'directory' manquant" in capsys.readouterr().err


def manifest(tmp_path):
    return json.loads((tmp_path / "out" / "air" / "2026-10" / "manifest.json").read_text())


def test_boundaries_are_downloaded_then_only_verified(env, http_server):
    tmp_path, cfg = env
    assert run_cli(cfg, tmp_path) == 0
    first = manifest(tmp_path)["inputs"]["boundaries"]
    assert first["status"] == "downloaded" and first["origin"] == http_server.url("/communes.geojson")
    assert run_cli(cfg, tmp_path) == 0
    second = manifest(tmp_path)["inputs"]["boundaries"]
    assert second["status"] == "unchanged" and second["sha256"] == first["sha256"]
    assert [p for p, _ in http_server.requests].count("/communes.geojson") == 2  # vérifié, pas retéléchargé
    assert http_server.requests[-1][1].get("If-None-Match")  # requête conditionnelle


def test_a_new_boundaries_version_is_picked_up(env, http_server, communes):
    tmp_path, cfg = env
    assert run_cli(cfg, tmp_path) == 0
    old = manifest(tmp_path)["inputs"]["boundaries"]
    http_server.files["/communes.geojson"] = communes.iloc[:1].to_json().encode()  # une commune de moins
    assert run_cli(cfg, tmp_path) == 0
    new = manifest(tmp_path)
    assert new["inputs"]["boundaries"]["status"] == "downloaded"
    assert new["inputs"]["boundaries"]["sha256"] != old["sha256"]
    assert new["communes"] == 1


def test_unreachable_server_falls_back_on_the_cached_boundaries(env, http_server, capsys):
    tmp_path, cfg = env
    assert run_cli(cfg, tmp_path) == 0
    http_server.status = 503
    assert run_cli(cfg, tmp_path) == 0
    assert manifest(tmp_path)["inputs"]["boundaries"]["status"] == "unverified"  # signalé dans la traçabilité


def test_unreachable_server_without_cache_fails_at_fetch(env, http_server, capsys):
    tmp_path, cfg = env
    http_server.status = 503
    assert run_cli(cfg, tmp_path) == 1
    printed = capsys.readouterr().out
    assert "fetch" in printed and "ÉCHEC" in printed and printed.count("ignorée") == 5
