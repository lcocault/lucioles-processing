# E4 — Interface Web de suivi (itération 4)

## US-4.1 — Liste des chaînes  `M` `à faire`
En tant qu'exploitant, je veux voir toutes les chaînes avec leur planification, leur dernière exécution et son statut afin d'évaluer d'un coup d'œil la santé du système.

## US-4.2 — Visualisation d'une chaîne  `M` `à faire`
En tant qu'exploitant, je veux voir les six étapes d'une chaîne et l'implémentation choisie pour chacune, afin de comprendre ce qu'elle fait.

## US-4.3 — Historique et détail d'une exécution  `M` `à faire`
En tant qu'exploitant, je veux consulter l'historique des exécutions et, pour chacune, le statut, la durée et l'erreur éventuelle de chaque étape afin de diagnostiquer un échec.
- La page se rafraîchit automatiquement tant qu'une exécution est en cours.

## US-4.4 — Déclenchement depuis l'interface  `S` `à faire`
En tant qu'exploitant, je veux lancer une chaîne (avec choix de période) depuis l'interface afin de ne pas manipuler l'API à la main.

## US-4.5 — Consultation des produits  `C` `à faire`
En tant qu'utilisateur, je veux voir les fichiers produits par une exécution (KML, etc.), les télécharger, et idéalement les prévisualiser sur une carte.

## Note technique
Proposition : pages rendues côté serveur (modèles Jinja + un peu de JS) servies par le même processus, qui consomment l'API de l'E3, avant d'envisager une SPA.
