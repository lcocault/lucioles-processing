# Historique des changements

Journal chronologique (le plus récent en premier) destiné à reprendre le travail depuis une autre
conversation. À compléter à chaque US livrée. Les points non résolus sont dans [open-points.md](open-points.md) ;
le backlog dans [user-stories/](user-stories/).

## 2026-11-08 — E2 Persistance PostgreSQL/PostGIS (code écrit, validation PostGIS en attente)
- **US-2.1 Schéma et migrations** (`en cours`) : migrations SQL numérotées dans
  `src/lucioles_processing/adapters/postgres/migrations/` ; tables `territory`, `indicator`, `indicator_value`,
  `chain_run`, `step_run`, vue `indicator_map` ; commandes `lucioles db migrate` / `lucioles db status`.
- **US-2.2 `IndicatorRepository` PostgreSQL** (`en cours`) : écriture transactionnelle et idempotente par
  (indicateur, période) ; méthode `find` pour relire. **Le port a changé** : `save(ctx, territories, values)`
  (les territoires portent la géométrie).
- **US-2.3 Historique des exécutions** (`fait`) : `PostgresRunListener` (upsert à chaque changement d'état) et
  `PostgresRunStore` (`get`, `recover_interrupted`).
- **US-2.4 Configuration** (`fait`) : URL par `LUCIOLES_DATABASE_URL` (jamais dans le YAML) ; si définie,
  `lucioles run` enregistre l'historique et refuse de tourner si le schéma n'est pas à jour (code 2).
- Outillage : `docker-compose.yml` (PostGIS), service PostGIS dans `.github/workflows/ci.yml`, doc dans README et
  `docs/ARCHITECTURE.md`.
- Tests : unitaires (URL, migrations, branchement) ; intégration `tests/integration/` et e2e
  `tests/e2e/test_postgres_chain.py`, ignorés sans `LUCIOLES_TEST_DATABASE_URL`. Les fixtures de base jetable sont dans
  `tests/conftest.py` (bases créées en UTF8 : une base SQL_ASCII renvoyait des `bytes`).
- Vérifié sur un PostgreSQL 15 **sans PostGIS** : schéma et contraintes (en retirant les parties PostGIS du SQL) et
  historique des exécutions. **Non vérifié** : tout ce qui utilise PostGIS.

## 2026-11-07/08 — E1 Socle hexagonal et chaîne générique (`fait`)
- **US-1.1/1.2** : `domain/model.py` (`Period`, `Territory`, `Observation`, `Dataset`, `IndicatorValue`, `ProductFile`),
  `domain/run.py` (`Step`, `Status`, `StepRun`, `ChainRun`), `domain/ports.py` (six ports + `RunListener`).
  Un test d'architecture interdit les dépendances d'E/S dans `domain/`.
- **US-1.3** : définition de chaîne en YAML (`config.py`, `ChainDefinition`) ; une implémentation (`use`) et des
  `params` par étape ; `save` et `distribute` valent `none` si omis ; registre (`application/registry.py`).
- **US-1.4** : `ChainExecutor` — espace de travail `workspace/<chaîne>/<période>/<id>/`, statut par étape, une étape
  en échec arrête la chaîne (suivantes `skipped`), les écouteurs défaillants n'interrompent rien.
- **US-1.5** : code existant porté en adaptateurs (`adapters/` : fetch, read, calculate, repository, build,
  distribute, registry). Sorties identiques à l'ancienne version (valeurs, niveaux, géométries, KML) contrôlées sur
  données synthétiques, par un script ponctuel non conservé.
- **US-1.6** : `lucioles run --config … --period … [--workspace …]` ; codes de sortie 0 / 1 (étape en échec) / 2
  (configuration). Les anciennes options `--admin --output --cache --formats` sont passées dans les `params` du YAML.
- Écart assumé : les exports ne gardent des colonnes ADMIN_EXPRESS que le code, le nom et le département.

## 2026-11-07 — Mise en place du dépôt
- Dépôt : https://github.com/lcocault/lucioles-processing.git (un premier essai visait par erreur
  `VicVEVO/Lucioles-lab` ; rien n'y a été poussé).
- Backlog rédigé dans `docs/user-stories/` (E1 à E5) ; `CLAUDE.md` impose tests unitaires et e2e.
- Environnement de développement : `~/.venvs/lucioles` (`pip install -e ".[dev]"`), `pytest`, `ruff check .`.
