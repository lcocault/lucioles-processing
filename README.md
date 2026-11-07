# Lucioles Processing

Chaîne de traitement **reproductible et automatisable** des indicateurs environnementaux
d'[Open Planet Facts](https://github.com/VicVEVO/Lucioles-lab) / Lucioles.

Elle reprend les principes algorithmiques et les technologies du laboratoire
[Lucioles-lab](../Lucioles-lab) (agrégation par commune de données d'observation de la Terre,
classement sur l'échelle OPF, exports GPKG / GeoJSON / KML / PMTiles) dans une approche
industrielle : configuration déclarative, ligne de commande, période en paramètre, tests, CI.

> **État : socle initial.** Le moteur est porté et testé ; les connecteurs de collecte réels, la
> composante tendance et la publication restent à faire (voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Placer le GeoPackage **ADMIN_EXPRESS** de l'IGN dans `data/inputs/` (non versionné).
Pour les tuiles : binaires `tippecanoe` et `pmtiles` dans le `PATH` (sinon l'export PMTiles est ignoré).

## Utilisation

```bash
lucioles run \
  --config configs/air_quality.example.yaml \
  --period 2026-10 \
  --admin data/inputs/ADMIN-EXPRESS.gpkg \
  --output output
```

Résultat : `output/air_quality/2026-10/` avec les couches cartographiques et un `manifest.json`.
Un indicateur se définit en YAML (sources, méthode d'agrégation, pondérations, seuils) :
voir [configs/air_quality.example.yaml](configs/air_quality.example.yaml).

## Licence

Apache 2.0, comme le laboratoire.
