#!/usr/bin/env bash
# Installe (ou met à jour) Lucioles Processing sur un hébergement AlwaysData, par SSH.
#   install.sh            première installation
#   install.sh update     mise à jour du code et des dépendances
# Variables : LUCIOLES_HOME (défaut ~/lucioles), LUCIOLES_REPO (défaut : dépôt GitHub), PYTHON (défaut python3)
set -euo pipefail

HOME_DIR="${LUCIOLES_HOME:-$HOME/lucioles}"
REPO="${LUCIOLES_REPO:-https://github.com/lcocault/lucioles-processing.git}"
PYTHON="${PYTHON:-python3}"

mkdir -p "$HOME_DIR"/{logs,workspace,cache,output,data/inputs}

if [ -d "$HOME_DIR/app/.git" ]; then
  git -C "$HOME_DIR/app" pull --ff-only
else
  git clone "$REPO" "$HOME_DIR/app"
fi

if [ ! -x "$HOME_DIR/venv/bin/python" ]; then
  "$PYTHON" -m venv "$HOME_DIR/venv"
fi
"$HOME_DIR/venv/bin/python" -m pip install --no-cache-dir --upgrade pip
# `[s3]` : distribution vers un bucket S3 ; installation non éditable (le dossier app/ peut être mis à jour)
"$HOME_DIR/venv/bin/python" -m pip install --no-cache-dir "$HOME_DIR/app[s3]"

if [ ! -f "$HOME_DIR/.env" ]; then
  cp "$HOME_DIR/app/deploy/alwaysdata/env.example" "$HOME_DIR/.env"
  chmod 600 "$HOME_DIR/.env"
  echo ">>> Éditez $HOME_DIR/.env (identifiants AWS, bucket) avant de lancer une chaîne."
fi
cp "$HOME_DIR/app/deploy/alwaysdata/run-chain.sh" "$HOME_DIR/run-chain.sh"
chmod +x "$HOME_DIR/run-chain.sh"
"$HOME_DIR/venv/bin/lucioles" --help > /dev/null && echo "Installation OK dans $HOME_DIR"
