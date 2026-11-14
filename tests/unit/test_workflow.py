"""Le workflow d'exécution fournit à `smoke.yaml` toutes les variables d'environnement qu'il référence."""

import re
from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/run-chain.yml")
SMOKE = Path("configs/smoke.yaml")


def load():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return data[True] if True in data else data["on"], data  # PyYAML lit `on` comme True


def test_declenchement_manuel_avec_config_et_periode():
    on, _ = load()
    inputs = on["workflow_dispatch"]["inputs"]
    assert {"config", "period", "sample_data"} <= set(inputs)


def test_secrets_jamais_en_clair():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "AKIA" not in text and "postgresql://" not in text
    env = load()[1]["jobs"]["run"]["env"]
    assert env["AWS_SECRET_ACCESS_KEY"] == "${{ secrets.AWS_SECRET_ACCESS_KEY }}"
    assert env["LUCIOLES_DATABASE_URL"] == "${{ secrets.LUCIOLES_DATABASE_URL }}"


def test_variables_de_la_chaine_de_test_toutes_fournies():
    env = load()[1]["jobs"]["run"]["env"]
    required = set(re.findall(r"\$\{([A-Z_]+)\}", SMOKE.read_text(encoding="utf-8")))  # sans valeur par défaut
    assert required <= set(env), required - set(env)


def test_permissions_minimales_et_une_seule_execution_par_chaine():
    _, data = load()
    assert data["permissions"] == {"contents": "read"}
    assert data["concurrency"]["cancel-in-progress"] is False
