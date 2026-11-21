# E5 — Distribution et déploiement (itération 5)

## US-5.1 — Distribution vers un dossier ou un serveur SFTP  `M` `à faire`
En tant qu'exploitant, je veux distribuer les fichiers produits vers une cible configurée afin de les rendre accessibles aux consommateurs.
- Adaptateurs `ProductDistributor` : dossier local, SFTP ; d'autres (S3, ...) pourront s'ajouter sans toucher au domaine.
- Une distribution en échec est signalée dans le statut de l'étape 6 et peut être rejouée sans recalcul.

## US-5.1b — Distribution vers un bucket Amazon S3  `M` `fait`
En tant qu'exploitant, je veux publier les fichiers produits dans un bucket S3 afin de les rendre accessibles sans serveur dédié.
- Adaptateur `s3` : `<préfixe>/<chaîne>/<période>/<fichier>` ; types MIME corrects ; réécriture idempotente.
- `<préfixe>/<chaîne>/latest.json` désigne la dernière période publiée (jamais écrasé par une période plus ancienne).
- Identifiants uniquement par l'environnement AWS standard (jamais dans le YAML) ; `endpoint_url` pour un S3 compatible.

## US-5.1c — Exécution des chaînes sur GitHub Actions  `S` `fait`
En tant qu'exploitant, je veux lancer une chaîne depuis GitHub (à la demande, puis planifiée) afin de l'exploiter sans serveur ni coût.
- Workflow `run-chain.yml` : paramètres `config`, `period`, `sample_data` ; secrets AWS et `LUCIOLES_DATABASE_URL` ; migration de la base ; une exécution à la fois par chaîne/période ; espace de travail joint en cas d'échec.
- Guide `docs/DEPLOIEMENT-GITHUB-ACTIONS.md` (Neon, IAM, secrets, test de fumée). Planification à activer avec la première chaîne réelle.

## US-5.1d — Sources lues depuis un bucket S3  `S` `fait`
En tant qu'exploitant, je veux que les données d'entrée volumineuses ou non publiques soient lues depuis mon bucket afin de ne pas dépendre d'un téléchargement manuel à chaque exécution.
- `url: s3://bucket/clé` (avec `{year}`, `{period}`) dans une source ou le fond administratif ; identifiants par l'environnement AWS ; mêmes garanties que HTTP (ETag, remplacement atomique, `unchanged`/`unverified`).

## US-5.2 — Image Docker et composition  `M` `à faire`
En tant qu'exploitant, je veux une image contenant l'application et ses dépendances (GDAL, tippecanoe, pmtiles) et un `docker compose` avec PostGIS afin de déployer en une commande.
- Volumes pour l'espace de travail et les produits ; configuration par variables d'environnement.

## US-5.3 — Observabilité  `S` `à faire`
En tant qu'exploitant, je veux des journaux structurés et des métriques (durée, succès/échec par chaîne) afin de superviser le service.

## US-5.4 — Alerte en cas d'échec  `S` `à faire`
En tant qu'exploitant, je veux être notifié (courriel ou webhook) lorsqu'une chaîne planifiée échoue.

## US-5.5 — Nettoyage de l'espace de travail  `C` `à faire`
En tant qu'exploitant, je veux une politique de rétention des espaces de travail et des produits anciens afin de maîtriser l'espace disque.
