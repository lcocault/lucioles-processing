# E2 — Persistance PostgreSQL / PostGIS (itération 2)

## US-2.1 — Schéma de base et migrations  `M` `à faire`
En tant qu'exploitant, je veux un schéma versionné par migrations (Alembic ou équivalent) afin de déployer la base de façon reproductible.
- Extension PostGIS activée ; tables `indicator`, `indicator_value` (commune, période, valeur, niveau, géométrie), `chain_run`, `step_run`.
- Les migrations s'appliquent sur une base vide en CI (conteneur `postgis/postgis`).

## US-2.2 — Adaptateur `IndicatorRepository` PostgreSQL  `M` `à faire`
En tant que chaîne, je veux enregistrer les indicateurs calculés afin de les interroger et de comparer les périodes.
- Écriture idempotente : relancer une même chaîne pour une même période remplace les valeurs, sans doublons.
- Lecture par indicateur, période et territoire ; test d'intégration sur PostGIS réel.

## US-2.3 — Historique des exécutions  `M` `à faire`
En tant qu'exploitant, je veux que chaque exécution et ses étapes soient enregistrées afin de consulter l'historique.
- Adaptateur `RunListener` écrivant dans `chain_run` / `step_run`.
- Les exécutions interrompues par un redémarrage du service sont marquées `failed` (ou `interrupted`) au démarrage.

## US-2.4 — Configuration de la connexion  `S` `à faire`
En tant qu'exploitant, je veux configurer la base par variables d'environnement afin de ne stocker aucun secret dans le dépôt.
