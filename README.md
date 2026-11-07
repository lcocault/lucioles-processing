# Lucioles Processing

Chaîne de traitement **reproductible et automatisable** des indicateurs environnementaux
d'[Open Planet Facts](https://github.com/VicVEVO/Lucioles-lab) / Lucioles.

Elle reprend les principes algorithmiques et les technologies du laboratoire
[Lucioles-lab](https://github.com/VicVEVO/Lucioles-lab) (agrégation par commune de données d'observation de la Terre,
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
lucioles run --config configs/air_quality.example.yaml --period 2026-10
```

Une **chaîne de traitement** est définie en YAML : l'indicateur, ses sources, et l'implémentation (`use`)
retenue pour chacune des six étapes (récupération, lecture, calcul, enregistrement, production des
fichiers, distribution). Voir [configs/air_quality.example.yaml](configs/air_quality.example.yaml).
Chaque exécution a son espace de travail `workspace/<chaîne>/<période>/<id>/` et affiche le statut de
chaque étape ; le code de sortie est non nul en cas d'échec (1) ou d'erreur de configuration (2).

## Licence

Apache 2.0, comme le laboratoire.
