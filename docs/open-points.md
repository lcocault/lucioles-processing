# Points ouverts

À jour au 2026-11-08. Retirer un point une fois résolu (et le noter dans [history.md](history.md)).

## À faire en priorité
1. **Valider E2 sur PostGIS.** Le serveur local (PostgreSQL 15) n'a pas l'extension PostGIS et Docker Desktop n'était
   pas démarré. Lancer :
   `docker compose up -d db` puis
   `LUCIOLES_TEST_DATABASE_URL=postgresql://lucioles:lucioles@localhost:5432/postgres pytest`
   (ou installer `postgresql-15-postgis-3`). Corriger ce qui casse, puis passer US-2.1 et US-2.2 à `fait`
   dans `docs/user-stories/E2-persistance.md`. Les 22 tests concernés sont ignorés tant que la variable est absente.
2. **Vérifier la CI GitHub** : le workflow `.github/workflows/ci.yml` (service PostGIS) n'a jamais tourné.
3. **Itération suivante : E3** (service en tâche de fond, API REST OpenAPI, planification) — voir
   [user-stories/E3-declenchement.md](user-stories/E3-declenchement.md). Au démarrage du service, appeler
   `PostgresRunStore.recover_interrupted()`.

## Décisions à prendre (de [user-stories/README.md](user-stories/README.md))
- Framework Web/API (proposition : FastAPI) et planificateur (APScheduler en processus, ou orchestrateur externe).
- Authentification de l'API et de l'interface (aucune, jeton, SSO ?).
- Premières cibles de distribution au-delà du dossier local (SFTP, S3 ?).
- Mono-instance ou plusieurs workers (file d'exécution, verrous).

## Dette technique et risques connus
- `tests/e2e` et `tests/integration` : le script de comparaison avec l'ancienne version (E1) n'est pas conservé en test.
- Les exports perdent les colonnes ADMIN_EXPRESS autres que code/nom/département.
- `.github/workflows/monthly.yml` : récupération d'ADMIN_EXPRESS, tippecanoe et pmtiles toujours en TODO.
- Connecteurs réels (Copernicus CAMS, stations de mesure, VIIRS), composante tendance et passage à toute la France
  (accélérer `zonal_mean`) : voir `docs/ARCHITECTURE.md`.
- Sans `LUCIOLES_DATABASE_URL`, `lucioles run` n'enregistre aucun historique (comportement implicite à documenter dans l'API/UI).
- Le champ `Period` ne gère que des périodes mensuelles.
- Dossiers temporaires laissés dans `/tmp` par une vérification ponctuelle (`/tmp/claude-1000/old`, `/tmp/tmp*`) : à supprimer à la main.
