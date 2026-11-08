# Instructions pour Claude — Lucioles Processing

## Contexte
Service hébergé exécutant des chaînes de traitement d'indicateurs environnementaux (voir
[docs/user-stories/](docs/user-stories/) pour la vision et le backlog, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
pour l'architecture). Architecture **hexagonale** : le domaine ne dépend d'aucune bibliothèque d'E/S.
Langue du projet (code commenté, docs, messages, commits) : **français**.

## Reprise de contexte
Avant de commencer, lire [docs/open-points.md](docs/open-points.md) (ce qui reste à faire ou à valider) et
[docs/history.md](docs/history.md) (ce qui a été fait). **Les mettre à jour à la fin de chaque session ou US.**

## Tests : impératif
- **Toute US livrée l'est avec ses tests unitaires.** Pas de code applicatif sans test qui le couvre ;
  un correctif de bug commence par un test qui échoue.
- **Quelques tests end-to-end** (`tests/e2e/`) vérifient les parcours complets (par exemple une chaîne lancée
  depuis la CLI ou l'API, de la définition YAML aux fichiers produits) avec des données synthétiques ;
  ils couvrent le cas nominal et au moins un cas d'échec par épopée.
- Les tests unitaires vont dans `tests/unit/`, sans réseau ni dépendance externe : utiliser les doubles en mémoire
  des ports. Les tests d'intégration (PostgreSQL/PostGIS, etc.) sont marqués `integration`.
- Tout est lancé avec `pytest` (environnement : `~/.venvs/lucioles`, `pip install -e ".[dev]"`) et `ruff check .`
  doit passer. Ne pas déclarer une US faite si l'un des deux échoue.

## Architecture
- `domain/` : modèle, ports, état d'exécution. **N'importe ni geopandas, ni shapely, ni psycopg, ni framework Web**
  (un test d'architecture le vérifie).
- `application/` : exécuteur de chaîne, registre des implémentations.
- `adapters/` : implémentations des ports (fichiers, base, export, distribution...).
- Une nouvelle capacité = un port dans le domaine + au moins un adaptateur + son enregistrement dans le registre.

## Méthode
- Travail incrémental : une US à la fois, un commit par US (message en français, impératif, avec l'identifiant `US-x.y`).
- À la fin d'une US, passer son statut à `fait` dans `docs/user-stories/` et mettre à jour la doc concernée.
- Ne pas pousser ni fusionner sans demande explicite de l'utilisateur.
