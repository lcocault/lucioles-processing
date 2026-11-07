# Architecture

```
collecte ──► extraction par commune ──► indicateur ──► exports ──► publication
(collect.py)   (engine.py)             (engine.py)   (export.py)   (à faire)
```

Un run = **un indicateur × une période** (`AAAA-MM`). Il est entièrement décrit par un fichier
YAML (`configs/`), sans notebook ni chemin codé en dur.

| Module | Rôle |
|---|---|
| `config.py` | Schéma et validation de la configuration |
| `collect.py` | Résolution des sources vers des fichiers locaux (chemin ou URL en cache) |
| `admin.py` | Fond administratif ADMIN_EXPRESS, filtré par départements |
| `engine.py` | Agrégation par commune (`zonal_mean`, `nearest_station`) et classement 0–4 |
| `export.py` | GPKG, GeoJSON, KML colorisé, PMTiles |
| `pipeline.py` | Orchestration d'un run et écriture du `manifest.json` |
| `cli.py` | Commande `lucioles run` |

Sorties : `output/<indicateur>/<période>/` (`.gpkg`, `.geojson`, `.kml`, `.pmtiles`, `manifest.json`).

## Écarts avec Lucioles-lab

- Une commune sans donnée vaut `NaN` / niveau `<NA>` (gris dans le KML), et non `0` (qui passait
  pour « excellent »).
- Le classement en niveaux est vectorisé et piloté par des seuils en configuration.
- La condition sur raster est évaluée sans `builtins`.
- Les périodes, URLs et chemins sont paramétrés ; chaque run écrit un manifeste.

## Reste à faire

1. Connecteurs réels (Copernicus CAMS, stations de mesure, pollution lumineuse VIIRS).
2. Composantes qualitative et **tendance** (comparaison avec les périodes précédentes).
3. Toute la France : accélérer `zonal_mean` raster (par exemple `exactextract`) et paralléliser.
4. Stockage versionné des sorties et publication des tuiles.
5. Planification (GitHub Actions `schedule` ou orchestrateur), alertes en cas d'échec.
6. Image Docker avec GDAL, tippecanoe et pmtiles.
