"""Les scripts de déploiement sont testés avec un faux `lucioles` : arguments, environnement, journal, verrou."""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT = Path("deploy/alwaysdata/run-chain.sh").resolve()
pytestmark = pytest.mark.skipif(not shutil.which("flock"), reason="flock indisponible")

FAKE = """#!/usr/bin/env bash
echo "args: $@"
echo "bucket: ${LUCIOLES_S3_BUCKET:-absent}"
echo "cwd: $(pwd)"
[ -n "${FAKE_FAIL:-}" ] && exit 3
[ -n "${FAKE_SLEEP:-}" ] && sleep "$FAKE_SLEEP"
exit 0
"""


@pytest.fixture
def home(tmp_path):
    (tmp_path / "venv" / "bin").mkdir(parents=True)
    fake = tmp_path / "venv" / "bin" / "lucioles"
    fake.write_text(FAKE)
    fake.chmod(0o755)
    (tmp_path / ".env").write_text("LUCIOLES_S3_BUCKET=mon-bucket\n")
    return tmp_path


def run(home, *args, **env):
    full = {**os.environ, "LUCIOLES_HOME": str(home), **env}
    return subprocess.run([str(SCRIPT), *args], check=False, env=full, capture_output=True, text=True)


def log(home, name="chaine"):
    return (home / "logs" / f"{name}.log").read_text()


def test_runs_with_env_file_and_default_period(home):
    result = run(home, "configs/chaine.yaml")
    assert result.returncode == 0
    text = log(home)
    assert f"args: run --config configs/chaine.yaml --period previous-month --workspace {home}/workspace" in text
    assert "bucket: mon-bucket" in text
    assert f"cwd: {home}" in text
    assert "début (période previous-month)" in text and "fin (code 0)" in text


def test_explicit_period(home):
    run(home, "configs/chaine.yaml", "2026-10")
    assert "--period 2026-10" in log(home)


def test_failure_exit_code_is_propagated_and_logged(home):
    result = run(home, "configs/chaine.yaml", FAKE_FAIL="1")
    assert result.returncode == 3
    assert "fin (code 3)" in log(home)


def test_usage_without_arguments(home):
    assert run(home).returncode == 64


def test_concurrent_runs_of_the_same_chain_are_skipped(home):
    first = subprocess.Popen([str(SCRIPT), "configs/chaine.yaml"],
                             env={**os.environ, "LUCIOLES_HOME": str(home), "FAKE_SLEEP": "2"})
    time.sleep(0.7)
    second = run(home, "configs/chaine.yaml")
    first.wait()
    assert second.returncode == 0
    assert "déjà en cours" in log(home)
    assert log(home).count("début") == 1


def test_different_chains_do_not_block_each_other(home):
    first = subprocess.Popen([str(SCRIPT), "configs/a.yaml"],
                             env={**os.environ, "LUCIOLES_HOME": str(home), "FAKE_SLEEP": "2"})
    time.sleep(0.7)
    run(home, "configs/b.yaml")
    first.wait()
    assert "fin (code 0)" in log(home, "b")


def test_old_run_directories_are_purged_but_recent_ones_and_other_files_are_kept(home):
    old, recent = home / "workspace/c/2026-09/old", home / "workspace/c/2026-10/recent"
    old.mkdir(parents=True)
    recent.mkdir(parents=True)
    keep = home / "workspace/c/note.txt"
    keep.write_text("x")
    past = time.time() - 10 * 86400
    os.utime(old, (past, past))
    run(home, "configs/chaine.yaml")
    assert not old.exists() and recent.exists() and keep.exists()
