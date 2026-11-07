# E5 — Distribution et déploiement (itération 5)

## US-5.1 — Distribution vers un dossier ou un serveur SFTP  `M` `à faire`
En tant qu'exploitant, je veux distribuer les fichiers produits vers une cible configurée afin de les rendre accessibles aux consommateurs.
- Adaptateurs `ProductDistributor` : dossier local, SFTP ; d'autres (S3, ...) pourront s'ajouter sans toucher au domaine.
- Une distribution en échec est signalée dans le statut de l'étape 6 et peut être rejouée sans recalcul.

## US-5.2 — Image Docker et composition  `M` `à faire`
En tant qu'exploitant, je veux une image contenant l'application et ses dépendances (GDAL, tippecanoe, pmtiles) et un `docker compose` avec PostGIS afin de déployer en une commande.
- Volumes pour l'espace de travail et les produits ; configuration par variables d'environnement.

## US-5.3 — Observabilité  `S` `à faire`
En tant qu'exploitant, je veux des journaux structurés et des métriques (durée, succès/échec par chaîne) afin de superviser le service.

## US-5.4 — Alerte en cas d'échec  `S` `à faire`
En tant qu'exploitant, je veux être notifié (courriel ou webhook) lorsqu'une chaîne planifiée échoue.

## US-5.5 — Nettoyage de l'espace de travail  `C` `à faire`
En tant qu'exploitant, je veux une politique de rétention des espaces de travail et des produits anciens afin de maîtriser l'espace disque.
