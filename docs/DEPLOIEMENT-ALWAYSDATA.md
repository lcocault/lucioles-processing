# Déploiement sur AlwaysData

Objectif : exécuter une chaîne **périodiquement** sur un hébergement AlwaysData et publier ses fichiers dans un
**bucket Amazon S3**. Le service permanent (API REST, interface Web — épopées E3/E4) n'existe pas encore : pour l'instant
on utilise la **tâche planifiée** d'AlwaysData, qui appelle `lucioles run`.

```
 tâche planifiée AlwaysData ──► run-chain.sh ──► lucioles run ──► (calcul) ──► bucket S3
   (mensuelle)                  .env, journal,                      workspace/      <préfixe>/<chaîne>/<période>/…
                                verrou, purge                                       <préfixe>/<chaîne>/latest.json
```

## 1. Prérequis et contraintes

| Sujet | À savoir |
|---|---|
| **Disque** | Une installation de production pèse **≈ 700 Mo** (scipy, pandas, rasterio…, mesuré), plus les données et l'espace de travail. Une offre à 100 Mo ne suffit pas ; vérifiez le disque de votre offre (prévoir ≥ 2 Go). |
| **Python** | ≥ 3.10. Dans l'administration AlwaysData : *Environnement > Python*, choisir 3.12 (ou 3.11). |
| **SSH** | Inclus dans les offres ; créer/activer un utilisateur SSH dans l'administration. |
| **Tâches planifiées** | Disponibles sur toutes les offres. |
| **Services permanents** | Réservés aux offres payantes (« Small » et plus) : utiles plus tard pour E3. |
| **PostgreSQL / PostGIS** | Facultatif pour cette première chaîne (`save: none`). Pour l'activer plus tard : créer la base dans l'administration, puis tester `CREATE EXTENSION postgis;` (disponibilité de PostGIS **non vérifiée**). |
| **PMTiles** | `tippecanoe` et `pmtiles` ne sont pas installés : retirer `pmtiles` des formats (déjà fait dans `configs/smoke.yaml`). |

## 2. Côté AWS : bucket et accès minimal

1. Créer le bucket (région au choix, ex. `eu-west-3`), **accès public bloqué** tant que vous n'avez pas décidé comment
   les consommateurs liront les fichiers (CloudFront, URL présignées, lecture publique d'un préfixe…).
2. Créer un utilisateur IAM dédié (sans console) avec cette politique, qui ne donne accès qu'à ce bucket :

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::NOM_DU_BUCKET" },
    { "Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject"], "Resource": "arn:aws:s3:::NOM_DU_BUCKET/*" }
  ]
}
```

   `s3:ListBucket` est nécessaire : sans lui, lire un `latest.json` encore absent renvoie « accès refusé » au lieu de
   « introuvable » et la première publication échoue. Pour limiter à un préfixe, remplacer `/*` par `/opf/*` et ajouter
   une condition `s3:prefix` sur `ListBucket`.
3. Créer une clé d'accès pour cet utilisateur ; elle sera copiée **uniquement** dans le `.env` du serveur (§4).

## 3. Installation (par SSH)

```bash
ssh <compte>@ssh-<compte>.alwaysdata.net          # hôte exact : voir l'administration AlwaysData
mkdir -p ~/lucioles && git clone https://github.com/lcocault/lucioles-processing.git ~/lucioles/app
PYTHON=python3 bash ~/lucioles/app/deploy/alwaysdata/install.sh
```

Le script crée `~/lucioles/{app,venv,logs,workspace,cache,data/inputs}`, installe l'application (avec l'extra `s3`,
sans cache pip pour économiser le disque) et copie `run-chain.sh`. Si le dépôt est privé, ajouter au préalable une
clé de déploiement (lecture seule) sur GitHub, ou copier le code par `scp`/`rsync` dans `~/lucioles/app`.

## 4. Configuration des secrets

```bash
nano ~/lucioles/.env     # créé depuis deploy/alwaysdata/env.example, permissions 600
```

Renseigner `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `LUCIOLES_S3_BUCKET`. Ce fichier n'est
jamais versionné ; les définitions de chaînes y font référence par `${LUCIOLES_S3_BUCKET}`.

## 5. Test de fumée (avant toute vraie donnée)

Vraies limites communales, mesures **synthétiques**, publication sous le préfixe `smoke/` :

```bash
cd ~/lucioles && set -a && . ./.env && set +a
./venv/bin/lucioles sample-data --period 2026-10
./run-chain.sh app/configs/smoke.yaml 2026-10 ; echo "code retour : $?"
tail -30 logs/smoke.log
aws s3 ls s3://$LUCIOLES_S3_BUCKET/smoke/ --recursive   # depuis votre poste, ou la console AWS
```

Attendu : `OK` pour les six étapes, 586 communes, et dans le bucket `smoke/smoke_test/2026-10/…` (GeoPackage, GeoJSON,
KML, `manifest.json`) ainsi que `smoke/smoke_test/latest.json`. Le premier lancement télécharge ≈ 10 Mo de limites
communales ; les suivants ne font que les revérifier.

## 6. Planification

Administration AlwaysData → *Tâches planifiées* → ajouter une tâche :

- **Commande** : `$HOME/lucioles/run-chain.sh app/configs/<votre_chaine>.yaml previous-month`
- **Fréquence** : mensuelle (par exemple le 5, à 06:00).

`previous-month` calcule la période à chaque lancement. `run-chain.sh` journalise dans `~/lucioles/logs/<chaîne>.log`,
refuse deux exécutions simultanées de la même chaîne et supprime les espaces de travail de plus de
`LUCIOLES_KEEP_DAYS` jours (7 par défaut).

## 7. Exploitation

| Besoin | Commande |
|---|---|
| Voir le dernier résultat | `tail -50 ~/lucioles/logs/<chaîne>.log` |
| Relancer une période | `~/lucioles/run-chain.sh app/configs/<chaîne>.yaml 2026-09` (republication idempotente) |
| Mettre à jour l'application | `bash ~/lucioles/app/deploy/alwaysdata/install.sh update` |
| Espace disque | `du -sh ~/lucioles/*` |

## 8. Dépannage

- **`ModuleNotFoundError` / commande introuvable** : relancer `install.sh` ; vérifier `~/lucioles/venv/bin/lucioles --help`.
- **`Variable d'environnement LUCIOLES_S3_BUCKET absente`** : `.env` incomplet.
- **`AccessDenied` à la distribution** : politique IAM (voir §2, notamment `ListBucket`), mauvaise région ou clé erronée.
  Les fichiers produits restent dans `workspace/` : relancer la chaîne une fois corrigé.
- **`NoSuchBucket`** : nom ou région du bucket.
- **Tuée en cours de route / manque de mémoire** : traiter moins de départements (`boundaries.departments`) ou passer à
  une offre avec plus de RAM ; le calcul raster sur toute la France est lourd.
- **`No space left on device`** : purger `~/lucioles/workspace` et `~/lucioles/cache`, ou changer d'offre.
