# E2 — Persistance PostgreSQL / PostGIS (itération 2)

## US-2.1 — Schéma de base et migrations  `M` `en cours`
En tant qu'exploitant, je veux un schéma versionné par migrations (Alembic ou équivalent) afin de déployer la base de façon reproductible.
- Extension PostGIS activée ; tables `indicator`, `indicator_value` (commune, période, valeur, niveau, géométrie), `chain_run`, `step_run`.
- Les migrations s'appliquent sur une base vide en CI (conteneur `postgis/postgis`).

## US-2.2 — Adaptateur `IndicatorRepository` PostgreSQL  `M` `en cours`
En tant que chaîne, je veux enregistrer les indicateurs calculés afin de les interroger et de comparer les périodes.
- Écriture idempotente : relancer une même chaîne pour une même période remplace les valeurs, sans doublons.
- Lecture par indicateur, période et territoire ; test d'intégration sur PostGIS réel.

## US-2.3 — Historique des exécutions  `M` `fait`
En tant qu'exploitant, je veux que chaque exécution et ses étapes soient enregistrées afin de consulter l'historique.
- Adaptateur `RunListener` écrivant dans `chain_run` / `step_run`.
- Les exécutions interrompues par un redémarrage du service sont marquées `failed` (ou `interrupted`) au démarrage.

## US-2.4 — Configuration de la connexion  `S` `fait`
En tant qu'exploitant, je veux configurer la base par variables d'environnement afin de ne stocker aucun secret dans le dépôt.

## État de la validation

Code et tests écrits pour les quatre US. Les tests d'intégration (`tests/integration/`, `tests/e2e/test_postgres_chain.py`)
exigent PostGIS et sont ignorés sans `LUCIOLES_TEST_DATABASE_URL`. US-2.1 et US-2.2 restent « en cours » tant
qu'ils n'ont pas tourné sur PostGIS (le schéma hors PostGIS et l'historique des exécutions ont été vérifiés sur un PostgreSQL 15 sans PostGIS).
