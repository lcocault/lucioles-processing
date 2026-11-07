# E3 — Exécution périodique et à la demande (itération 3)

## US-3.1 — Service en tâche de fond  `M` `à faire`
En tant qu'exploitant, je veux une commande `lucioles serve` qui démarre un processus longue durée (API + planificateur + exécution des chaînes)
afin de l'héberger sur un serveur.
- Arrêt propre sur SIGTERM : les exécutions en cours se terminent ou sont marquées interrompues.
- Endpoint `GET /health` pour la supervision.

## US-3.2 — Exécution asynchrone et file d'exécution  `M` `à faire`
En tant que service, je veux exécuter les chaînes hors du thread de requête, avec une limite de concurrence, afin de ne pas bloquer l'API.
- Une même chaîne ne peut pas tourner deux fois en parallèle pour la même période (verrou) ; la seconde demande est refusée ou mise en file selon la politique configurée.

## US-3.3 — API REST de déclenchement (OpenAPI)  `M` `à faire`
En tant que client, je veux déclencher une chaîne par `POST /chains/{name}/runs` avec une période optionnelle afin de lancer un traitement à la demande.
- Réponse `202` avec l'identifiant d'exécution ; `404` chaîne inconnue ; `409` si déjà en cours ; `422` si paramètres invalides.
- Contrat OpenAPI 3 publié (`/openapi.json`) et versionné dans le dépôt ; un test vérifie qu'il correspond à l'implémentation.

## US-3.4 — API REST de consultation  `M` `à faire`
En tant que client, je veux lister les chaînes (`GET /chains`), consulter une exécution (`GET /runs/{id}`) et l'historique (`GET /chains/{name}/runs`), afin de suivre les traitements.
- Pagination et filtre par statut ; le détail inclut le statut de chaque étape.

## US-3.5 — Planification périodique  `M` `à faire`
En tant qu'exploitant, je veux associer une expression cron à une chaîne (dans sa définition) afin qu'elle s'exécute automatiquement.
- La période traitée par défaut est déterminée par une règle (par exemple « mois précédent »).
- Une exécution manquée pendant une indisponibilité est rattrapée ou ignorée selon un paramètre.
- Les déclenchements planifiés et manuels sont distingués dans l'historique (`trigger = schedule|api|cli`).

## US-3.6 — Annulation d'une exécution  `C` `à faire`
En tant qu'exploitant, je veux annuler une exécution en cours via `DELETE /runs/{id}` ou `POST /runs/{id}/cancel`.

## US-3.7 — Protection de l'API  `S` `à faire`
En tant qu'exploitant, je veux protéger les endpoints de déclenchement (jeton d'API) afin d'éviter un usage non autorisé. *Dépend de la question ouverte sur l'authentification.*
