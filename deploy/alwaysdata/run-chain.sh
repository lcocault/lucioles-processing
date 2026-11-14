#!/usr/bin/env bash
# Lance une chaîne (pensé pour une tâche planifiée AlwaysData) : charge l'environnement, journalise,
# empêche deux exécutions simultanées de la même chaîne et purge les anciens espaces de travail.
#   run-chain.sh <configs/chaine.yaml> [période]     période : AAAA-MM | previous-month (défaut) | current-month
# Variables : LUCIOLES_HOME (défaut ~/lucioles), LUCIOLES_KEEP_DAYS (défaut 7 : conservation des espaces de travail)
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <configs/chaine.yaml> [période]" >&2
  exit 64
fi
HOME_DIR="${LUCIOLES_HOME:-$HOME/lucioles}"
CONFIG="$1"
PERIOD="${2:-previous-month}"
NAME="$(basename "$CONFIG" .yaml)"

set -a
# shellcheck disable=SC1091
[ -f "$HOME_DIR/.env" ] && . "$HOME_DIR/.env"
set +a

cd "$HOME_DIR"
mkdir -p logs workspace
LOG="logs/$NAME.log"

exec 9> "$HOME_DIR/.lock-$NAME"
if ! flock -n 9; then
  echo "$(date -u +%FT%TZ) $NAME : déjà en cours, exécution ignorée" >> "$LOG"
  exit 0
fi

echo "$(date -u +%FT%TZ) $NAME : début (période $PERIOD)" >> "$LOG"
status=0
"$HOME_DIR/venv/bin/lucioles" run --config "$CONFIG" --period "$PERIOD" --workspace "$HOME_DIR/workspace" \
  >> "$LOG" 2>&1 || status=$?
echo "$(date -u +%FT%TZ) $NAME : fin (code $status)" >> "$LOG"

# Purge : uniquement les dossiers d'exécution (workspace/<chaîne>/<période>/<id>) plus vieux que N jours
find "$HOME_DIR/workspace" -mindepth 3 -maxdepth 3 -type d -mtime "+${LUCIOLES_KEEP_DAYS:-7}" \
  -exec rm -rf {} + 2>/dev/null || true
exit "$status"
