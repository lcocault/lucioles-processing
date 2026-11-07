# User stories

Vision : héberger Lucioles Processing sur un serveur, en tâche de fond, pour
1. activer **périodiquement** des chaînes de traitement ;
2. les activer **à la demande** via une API REST décrite en **OpenAPI** ;
3. visualiser les chaînes et le **statut de leurs activations** dans une interface Web.

## Chaîne de traitement (définition générique)

| # | Étape | Port (abstraction) |
|---|---|---|
| 1 | Récupération des données externes dans un espace de travail | `DataFetcher` |
| 2 | Lecture et mapping vers le modèle interne | `DataReader` |
| 3 | Calcul des indicateurs | `IndicatorCalculator` |
| 4 | Enregistrement en PostgreSQL / PostGIS | `IndicatorRepository` |
| 5 | Production des fichiers de diffusion (KML, ...) | `ProductPublisher`/`ProductBuilder` |
| 6 | Distribution des fichiers | `ProductDistributor` |

Une chaîne = une définition (étapes + implémentations choisies + paramètres) ; chaque port a
une ou plusieurs implémentations (adaptateurs), conformément à l'architecture hexagonale.

## Épopées et ordre de réalisation

| Itération | Épopée | Fichier | Valeur livrée |
|---|---|---|---|
| 1 | E1 Socle hexagonal | [E1-socle.md](E1-socle.md) | Chaîne générique exécutable en CLI, code existant porté en adaptateurs |
| 2 | E2 Persistance | [E2-persistance.md](E2-persistance.md) | Indicateurs et historique d'exécutions dans PostgreSQL/PostGIS |
| 3 | E3 Exécution à la demande et périodique | [E3-declenchement.md](E3-declenchement.md) | Service en tâche de fond, API REST OpenAPI, planification |
| 4 | E4 Interface Web | [E4-interface-web.md](E4-interface-web.md) | Visualisation des chaînes et des statuts |
| 5 | E5 Distribution et déploiement | [E5-distribution-deploiement.md](E5-distribution-deploiement.md) | Distribution des fichiers, Docker, exploitation |

## Conventions

- Identifiants `US-<épopée>.<n>` ; priorité MoSCoW (M/S/C) ; statut : `à faire`, `en cours`, `fait`.
- Chaque US a des critères d'acceptation vérifiables par un test automatisé.
- Définition de « fait » : code, tests, documentation à jour, CI verte.
- On réalise une itération à la fois ; les US des itérations suivantes sont volontairement moins détaillées
  et seront affinées avant d'être entamées.

## Questions ouvertes

- Choix du framework Web/API (proposition : FastAPI, qui génère OpenAPI) et du planificateur (APScheduler en
  processus, ou orchestrateur externe).
- Authentification de l'API et de l'interface (aucune, jeton, SSO ?).
- Cibles de distribution à supporter en premier (système de fichiers, SFTP, S3, ...).
- Mono-instance ou plusieurs workers (impacte la file d'exécution et les verrous).
