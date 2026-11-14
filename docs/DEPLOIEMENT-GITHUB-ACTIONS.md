# Déploiement gratuit : GitHub Actions + S3 + Neon

Le calcul tourne sur un runner GitHub (dépôt public : minutes gratuites), les fichiers sont publiés dans un bucket S3,
les indicateurs et l'historique des exécutions vont dans une base PostgreSQL/PostGIS hébergée par Neon.
Aucun serveur à administrer. Workflow : [.github/workflows/run-chain.yml](../.github/workflows/run-chain.yml).

```
GitHub Actions (runner jetable)
  lucioles db migrate ──────────────► Neon (PostgreSQL + PostGIS) : indicateurs, historique
  lucioles run --config … --period …
        └─ distribute: s3 ──────────► Bucket S3 : <préfixe>/<chaîne>/<période>/…  + latest.json
```

## 1. Base de données Neon
1. Créer un compte sur <https://neon.com> et un projet (région européenne, la plus proche de votre bucket).
2. Dans **Connection details**, **désactiver « Connection pooling »** et copier l'URL directe, du type
   `postgresql://utilisateur:motdepasse@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`.
   (Le pooler en mode transaction n'est pas adapté aux migrations.)
3. Le rôle fourni par Neon peut exécuter `CREATE EXTENSION postgis` : la migration s'en charge. Si elle échoue, lancer
   `CREATE EXTENSION postgis;` dans le **SQL Editor** de Neon et rejouer.
4. La base se met en veille après quelques minutes d'inactivité (offre gratuite) ; la première connexion prend
   quelques secondes, sans conséquence pour un traitement mensuel.

## 2. Bucket S3 et clés AWS
1. Bucket existant (noter son **nom** et sa **région**, par exemple `eu-west-3`).
2. IAM → utilisateur dédié (pas de droits console) avec cette politique, limitée au bucket :
   ```json
   {"Version": "2012-10-17", "Statement": [
     {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::NOM-DU-BUCKET"},
     {"Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject"], "Resource": "arn:aws:s3:::NOM-DU-BUCKET/*"}
   ]}
   ```
3. Créer une clé d'accès pour cet utilisateur (cas d'usage « application hors AWS »).
4. Les résultats sont **privés** par défaut. Les rendre lisibles (préfixe public, CloudFront ou URL présignées) est un
   choix à faire à part (voir [open-points.md](open-points.md)).

## 3. Secrets et variables GitHub
Dépôt → **Settings → Secrets and variables → Actions**.

| Type | Nom | Valeur |
|---|---|---|
| Secret | `AWS_ACCESS_KEY_ID` | clé d'accès IAM |
| Secret | `AWS_SECRET_ACCESS_KEY` | clé secrète IAM |
| Secret | `LUCIOLES_DATABASE_URL` | URL directe Neon (facultatif : sans elle, rien n'est enregistré en base) |
| Variable | `AWS_DEFAULT_REGION` | par exemple `eu-west-3` |
| Variable | `LUCIOLES_S3_BUCKET` | nom du bucket |

Le dépôt étant public, ne jamais mettre ces valeurs dans un fichier versionné, un commentaire ou une issue.
Les journaux GitHub masquent les secrets mais sont publics.

## 4. Test de fumée
Onglet **Actions → Exécuter une chaîne → Run workflow** avec les valeurs par défaut
(`configs/smoke.yaml`, `previous-month`, données synthétiques). Résultat attendu :
- les 6 étapes `ok` dans le journal, 586 communes ;
- dans le bucket : `smoke/smoke_test/<période>/` (gpkg, geojson, kml, manifeste) et `smoke/smoke_test/latest.json` ;
- dans Neon (SQL Editor) : `SELECT * FROM schema_migration;`, puis `indicator_value`, `chain_run` et `step_run` remplies.

Relancer la même période doit réussir sans doublon (écritures idempotentes).

## 5. Chaîne réelle et planification
Une fois une chaîne réelle disponible (voir US-1.8 et US-1.9), lancer le même workflow avec son YAML, puis
décommenter `schedule` dans le workflow (le 5 de chaque mois, 06:00 UTC). Les sources annuelles (INERIS, lumière)
ne demandent qu'un déclenchement par an. GitHub désactive les planifications d'un dépôt resté 60 jours sans activité.

## Dépannage
- **`Variable d'environnement LUCIOLES_S3_BUCKET absente`** : variable (et non secret) non créée, ou nom différent.
- **`AccessDenied`** : politique IAM, nom de bucket ou région incorrects (la politique doit inclure `s3:ListBucket`).
- **`could not translate host name` / délai de connexion** : mauvaise URL Neon ; utiliser l'URL directe avec `sslmode=require`.
- **Échec du workflow** : l'espace de travail est joint en artefact (3 jours) pour analyser les fichiers intermédiaires.
