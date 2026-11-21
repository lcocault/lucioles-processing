import pytest

from lucioles_processing.config import (
    BoundariesConfig,
    IndicatorSpec,
    SourceConfig,
    load_chain_definition,
    parse_chain_definition,
)
from lucioles_processing.domain.run import Step
from tests.doubles import raw_definition


def test_example_config_loads():
    d = load_chain_definition("configs/air_quality.example.yaml")
    assert d.name == "air_quality"
    assert d.indicator.name == "air_quality"
    assert set(d.sources) == {"no2", "pm10"}
    assert set(d.steps) == set(Step)


def test_optional_steps_default_to_none():
    d = parse_chain_definition(raw_definition())
    assert d.steps[Step.SAVE].use == "none"
    assert d.steps[Step.DISTRIBUTE].use == "none"


def test_step_params_are_kept():
    d = parse_chain_definition(raw_definition(build={"use": "x", "params": {"formats": ["kml"]}}))
    assert d.steps[Step.BUILD].params == {"formats": ["kml"]}


@pytest.mark.parametrize("missing", ["chain", "indicator", "sources", "boundaries", "steps"])
def test_missing_top_level_key(missing):
    raw = raw_definition()
    del raw[missing]
    with pytest.raises(ValueError, match=missing):
        parse_chain_definition(raw)


@pytest.mark.parametrize("step", ["fetch", "read", "calculate", "build"])
def test_mandatory_step_missing(step):
    raw = raw_definition()
    del raw["steps"][step]
    with pytest.raises(ValueError, match=f"obligatoire absente : '{step}'"):
        parse_chain_definition(raw)


def test_unknown_step():
    with pytest.raises(ValueError, match="Étapes inconnues"):
        parse_chain_definition(raw_definition(teleport={"use": "x"}))


def test_step_without_use():
    with pytest.raises(ValueError, match="'use' est obligatoire"):
        parse_chain_definition(raw_definition(build={"params": {}}))


def test_weights_for_unknown_source():
    raw = raw_definition()
    raw["indicator"]["weights"] = {"zzz": 1.0}
    with pytest.raises(ValueError, match="sources inconnues"):
        parse_chain_definition(raw)


def test_not_a_mapping():
    with pytest.raises(ValueError, match="dictionnaire"):
        parse_chain_definition(["a"])


def test_unknown_method():
    with pytest.raises(ValueError, match="inconnue"):
        SourceConfig(name="x", method="magic", path="a.tif")


def test_source_requires_path_or_url():
    with pytest.raises(ValueError, match="path"):
        SourceConfig(name="x", method="zonal_mean")


def test_nearest_station_requires_dims():
    with pytest.raises(ValueError, match="dims"):
        SourceConfig(name="x", method="nearest_station", path="a.csv", field="v")


def test_thresholds_must_be_sorted():
    with pytest.raises(ValueError):
        IndicatorSpec(name="i", weights={}, thresholds=[4, 3, 2, 1])


def test_example_boundaries_are_downloaded_by_default():
    b = load_chain_definition("configs/air_quality.example.yaml").boundaries
    assert b.url.startswith("https://") and b.path is None
    assert (b.code_field, b.name_field, b.department_field) == ("code", "nom", "departement")
    assert b.refresh == "if_changed" and b.departments == ["31"]


def test_boundaries_defaults_are_admin_express():
    b = BoundariesConfig(path="x.gpkg", departments=[31, "2A"])
    assert (b.code_field, b.name_field, b.department_field) == (
        "code_insee", "nom_officiel", "code_insee_du_departement")
    assert b.departments == ["31", "2A"] and b.refresh == "if_changed"


@pytest.mark.parametrize("kwargs", [{}, {"path": "a", "url": "http://x"}])
def test_boundaries_need_exactly_one_origin(kwargs):
    with pytest.raises(ValueError, match="exactement un"):
        BoundariesConfig(**kwargs)


def test_boundaries_unknown_refresh():
    with pytest.raises(ValueError, match="refresh"):
        BoundariesConfig(path="a", refresh="parfois")


def test_boundaries_is_a_reserved_source_name():
    raw = raw_definition()
    raw["sources"]["boundaries"] = {"method": "zonal_mean", "path": "x.tif"}
    with pytest.raises(ValueError, match="réservé"):
        parse_chain_definition(raw)


def test_expand_env_in_nested_structures():
    from lucioles_processing.config import expand_env

    env = {"BUCKET": "mon-bucket", "EMPTY": ""}
    raw = {"a": "${BUCKET}", "b": ["x-${BUCKET}-y", 3], "c": {"d": "${MISSING:-def}", "e": "${EMPTY:-vide}"}}
    assert expand_env(raw, env) == {"a": "mon-bucket", "b": ["x-mon-bucket-y", 3], "c": {"d": "def", "e": "vide"}}


def test_expand_env_leaves_period_placeholders_alone():
    from lucioles_processing.config import expand_env

    assert expand_env("data/no2_{period}_${Y:-2026}.tif", {}) == "data/no2_{period}_2026.tif"


def test_expand_env_missing_variable_is_explicit():
    from lucioles_processing.config import expand_env

    with pytest.raises(ValueError, match="LUCIOLES_S3_BUCKET"):
        expand_env({"bucket": "${LUCIOLES_S3_BUCKET}"}, {})


def test_load_chain_definition_expands_env(tmp_path, monkeypatch):
    import yaml

    raw = raw_definition(distribute={"use": "s3", "params": {"bucket": "${LUCIOLES_S3_BUCKET}"}})
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(raw))
    monkeypatch.setenv("LUCIOLES_S3_BUCKET", "bucket-prod")
    assert load_chain_definition(path).steps[Step.DISTRIBUTE].params == {"bucket": "bucket-prod"}
    monkeypatch.delenv("LUCIOLES_S3_BUCKET")
    with pytest.raises(ValueError, match="LUCIOLES_S3_BUCKET"):
        load_chain_definition(path)


def test_light_pollution_chain_is_valid_and_buildable(monkeypatch):
    from lucioles_processing.adapters.registry import default_registry
    from lucioles_processing.domain.model import Period

    monkeypatch.setenv("LUCIOLES_S3_BUCKET", "mon-bucket")
    definition = load_chain_definition("configs/light_pollution.yaml")
    assert definition.name == "light_pollution"
    source = definition.sources["light"]
    assert source.url.format(**Period(2025).fields()) == "s3://mon-bucket/inputs/vnl/vnl_2025_france.tif"
    assert definition.steps[Step.SAVE].use == "none"  # `LUCIOLES_SAVE` absent : pas d'écriture en base
    default_registry().build(definition)  # toutes les implémentations nommées existent


def test_light_pollution_chain_saves_to_postgres_when_requested(monkeypatch):
    monkeypatch.setenv("LUCIOLES_S3_BUCKET", "mon-bucket")
    monkeypatch.setenv("LUCIOLES_SAVE", "postgres")
    assert load_chain_definition("configs/light_pollution.yaml").steps[Step.SAVE].use == "postgres"
