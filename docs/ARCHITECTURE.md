# Architecture

Architecture **hexagonale** : le domaine définit le modèle et six ports (un par étape de la chaîne) ;
les adaptateurs les implémentent ; un registre associe le nom d'une implémentation (`use:` dans le YAML)
à sa fabrique. Vision et backlog : [user-stories/](user-stories/).

```
 fetch ──► read ──► calculate ──► save ──► build ──► distribute        (ChainExecutor)
 DataFetcher DataReader IndicatorCalculator IndicatorRepository ProductBuilder ProductDistributor  (ports)
```

| Paquet | Rôle |
|---|---|
| `domain/model.py` | `Period`, `Territory`, `Observation`, `Dataset`, `IndicatorValue`, `ProductFile` |
| `domain/run.py` | `Step`, `Status`, `StepRun`, `ChainRun` (état d'une exécution) |
| `domain/ports.py` | Les six ports, `StepContext`, `RunListener` |
| `config.py` | `ChainDefinition` : parsing et validation du YAML |
| `application/registry.py` | Registre des implémentations, construction des composants |
| `application/executor.py` | `ChainExecutor` : enchaîne les étapes, trace les statuts, notifie les écouteurs |
| `adapters/download.py` | Téléchargement conditionnel (ETag/Last-Modified), repli sur la copie locale |
| `adapters/` | `fetch` (fichiers/URL), `read` (agrégation par commune), `calculate` (somme pondérée), `repository` (aucun/mémoire), `build` (GPKG, GeoJSON, KML, PMTiles, manifeste), `distribute` (dossier local) |
| `adapters/postgres/` | `database` (connexion, migrations SQL numérotées), `repository` (indicateurs + territoires PostGIS), `run_history` (historique des exécutions, reprise après arrêt) |
| `cli.py` | Commandes `lucioles run`, `lucioles db migrate/status` |

Règle vérifiée par un test (`tests/unit/test_architecture.py`) : `domain/` n'importe aucune bibliothèque d'E/S.
Ajouter une capacité = un port (si nouvelle étape) + un adaptateur + son enregistrement dans
`adapters/registry.py`.

Une exécution : un espace de travail dédié, un statut par étape (`pending`, `running`, `succeeded`,
`failed`, `skipped`) ; une étape en échec arrête la chaîne et les suivantes sont `skipped`.

## Base de données

Schéma (`adapters/postgres/migrations/`) : `territory` (code, nom, géométrie `EPSG:4326`), `indicator`,
`indicator_value` (clé `(indicateur, période, territoire)`, période = 1er jour du mois), vue `indicator_map`
(valeurs + géométrie), `chain_run` et `step_run` (historique). L'écriture des indicateurs est transactionnelle
et remplace les valeurs de l'(indicateur, période). Au redémarrage du service, `PostgresRunStore.recover_interrupted()`
marque en échec les exécutions restées en cours.

## Écarts avec Lucioles-lab

- Une commune sans donnée vaut `NaN` / niveau `<NA>` (gris dans le KML), et non `0` (qui passait
  pour « excellent »).
- Le classement en niveaux est piloté par des seuils en configuration.
- La condition sur raster est évaluée sans `builtins`.
- Les périodes, URLs et chemins sont paramétrés ; chaque run écrit un manifeste.

## Reste à faire

Voir le backlog [user-stories/](user-stories/). Côté traitement : connecteurs réels (Copernicus CAMS,
stations, VIIRS), composante tendance, passage à toute la France (accélérer `zonal_mean`).
