# E1 — Socle hexagonal et chaîne générique (itération 1)

Objectif : isoler le domaine et définir la chaîne en 6 étapes, sans dépendance à PostgreSQL, au Web
ni au planificateur. Le code actuel (`collect`, `engine`, `export`, `pipeline`) devient des adaptateurs.

## US-1.1 — Modèle de domaine interne  `M` `fait`
En tant que développeur, je veux un modèle de données interne indépendant des formats sources
(`Indicator`, `IndicatorValue`, `Period`, `Territory`, `ProductFile`), afin que le calcul ne dépende d'aucune
bibliothèque d'entrée/sortie.
- Le paquet `domain` n'importe ni geopandas, ni psycopg, ni framework Web (vérifié par un test d'architecture).
- Les objets sont immuables et validés (période `AAAA-MM`, niveau 0–4 ou absent).

## US-1.2 — Ports de la chaîne  `M` `fait`
En tant que développeur, je veux six interfaces (`DataFetcher`, `DataReader`, `IndicatorCalculator`,
`IndicatorRepository`, `ProductBuilder`, `ProductDistributor`) afin de découpler les étapes de leurs implémentations.
- Chaque port est une classe abstraite/`Protocol` documentée avec entrées et sorties typées.
- Des doubles de test en mémoire existent pour chaque port.

## US-1.3 — Définition générique d'une chaîne  `M` `à faire`
En tant qu'exploitant, je veux décrire une chaîne en YAML (nom, étapes, implémentation de chaque étape, paramètres)
afin d'ajouter une chaîne sans modifier le code.
- Schéma validé ; message clair si une implémentation est inconnue ou un paramètre manquant.
- Un registre associe un nom d'implémentation à un adaptateur.
- Le fichier `configs/air_quality.example.yaml` est migré vers ce format.

## US-1.4 — Exécuteur de chaîne  `M` `à faire`
En tant qu'exploitant, je veux qu'un exécuteur enchaîne les six étapes dans un espace de travail dédié à l'exécution,
afin d'obtenir un résultat traçable.
- Chaque exécution a un identifiant, un état (`pending`, `running`, `succeeded`, `failed`) et un statut par étape
  (début, fin, durée, erreur).
- Une étape en échec arrête la chaîne et l'erreur est conservée ; les étapes suivantes sont `skipped`.
- Les événements d'exécution sont émis via un port `RunListener` (utilisé plus tard par la persistance et l'UI).

## US-1.5 — Portage des traitements existants en adaptateurs  `M` `à faire`
En tant que développeur, je veux porter `collect.py`, `engine.py` et `export.py` en adaptateurs des ports,
afin que la chaîne qualité de l'air d'exemple produise les mêmes résultats qu'aujourd'hui.
- Les tests existants passent ; les sorties (GPKG, GeoJSON, KML) sont identiques à celles de la version actuelle.
- L'étape de distribution dispose d'un adaptateur « dossier local » minimal.

## US-1.6 — Commande `lucioles run` sur le nouveau socle  `S` `à faire`
En tant qu'utilisateur, je veux conserver la CLI actuelle, qui utilise désormais l'exécuteur, afin de ne pas perdre
la voie d'exécution manuelle.
- `lucioles run --config ... --period ...` fonctionne et affiche le statut par étape.
- Le code de sortie est non nul en cas d'échec.
