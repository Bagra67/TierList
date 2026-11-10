[English](monitoring.md) | Français

# Suivi des erreurs (Sentry)

Les erreurs de production, du backend comme du navigateur, sont envoyées à **Sentry**, qui les regroupe, garde leur pile d'appels et prévient par e-mail d'une nouvelle erreur. Rien n'est envoyé tant que `SENTRY_DSN` est vide : le local, les tests et la CI n'envoient jamais rien.

Les logs eux-mêmes (INFO et au-dessus) ne vont toujours que dans la console du pod ([README du backend, Logs](../../backend/README.fr.md#10-logs)).

## 1. Ce qui est envoyé

| Source     | Envoyé                                                                                                                                                                                                                                   | Où dans le code                                                    |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Backend    | Chaque log `ERROR`, avec son exception : les loggers `app.*` de l'application (erreurs non gérées journalisées par `core/errors.py`, qui répond une 500 générique ; échecs des tâches de nuit), mais aussi uvicorn et les bibliothèques. | `app/core/monitoring.py` (`LoggingIntegration(event_level=ERROR)`) |
| Navigateur | Plantages du rendu interceptés par la limite d'erreur, avec la pile de composants React.                                                                                                                                                 | `src/components/ErrorBoundary.tsx` (`componentDidCatch`)           |
| Navigateur | Requêtes en échec hors 4xx (erreur serveur, backend injoignable). Les 4xx attendues sont affichées par la page et ne sont pas envoyées.                                                                                                  | `src/api/queryClient.ts`                                           |
| Navigateur | Erreurs non interceptées et promesses rejetées (intégrations par défaut du SDK).                                                                                                                                                         | `src/monitoring/sentry.ts`                                         |

Chaque événement porte la **version** (`APP_RELEASE` : `vX.Y.Z` ou `develop-<commit>`) et l'**environnement** (`SENTRY_ENVIRONMENT` : `staging` ou `production`). Les avertissements ne sont pas envoyés, pour garder le quota gratuit pour les erreurs.

## 2. Ce qui n'est pas envoyé

La politique de confidentialité promet des rapports d'erreur sans adresse IP, cookies ni contenu saisi. Le code le garantit :

- **Backend** (`configure_sentry`) : `send_default_pii=False` (ni IP de l'utilisateur, ni cookie), `max_request_body_size="never"` (aucun corps de requête : mots de passe, e-mails), `include_local_variables=False` (aucune variable des cadres de la pile), et `remove_request_personal_data`, sur les erreurs comme sur les transactions, retire la query string (un `code` Google, un e-mail cherché par un modérateur), les cookies et tous les en-têtes sauf `User-Agent` (derrière Cloudflare, `Cf-Connecting-Ip` contient l'IP de l'utilisateur ; un `Referer` peut contenir un token de réinitialisation du mot de passe). L'engine de la base a `hide_parameters=True` (`db/session.py`) : une erreur SQL ne recopie pas les valeurs de sa requête (e-mails, texte saisi) dans son message.
- **Navigateur** (`buildSentryOptions`) : depuis la v11 du SDK, `dataCollection` collecte par défaut ; `userInfo`, `cookies`, `httpHeaders`, `httpBodies` et `urlQueryParams` sont tous désactivés. `removeUrlFragment` et `removeBreadcrumbUrlFragments` retirent le fragment de l'URL de l'événement et des breadcrumbs de navigation et de requête : le lien personnel d'invité y porte son token (`/r/<code>#guest=…`). Les breadcrumbs de la console sont désactivés (`withoutConsoleBreadcrumbs`) : un message de la console peut contenir une clé de requête, comme un e-mail cherché. Ni Session Replay, ni tracing.
- **Projet Sentry** : _Settings → Security & Privacy → Prevent Storing of IP Addresses_ doit être activé, sinon le serveur de Sentry enregistre l'adresse IP depuis laquelle le navigateur se connecte.

Toujours envoyé : le chemin de l'URL, donc les codes de salle (`/r/<code>`) et les liens de résultats (`/results/<token>`), faits pour être partagés et sans donnée personnelle.

Le suivi des performances est désactivé (`SENTRY_TRACES_SAMPLE_RATE=0`) ; il peut être activé côté backend sans nouvelle version.

## 3. Comment le navigateur reçoit ses réglages

Un même build du frontend sert le staging et la production : le navigateur ne peut donc pas recevoir son DSN au build. `main.tsx` appelle `initMonitoring()`, qui lit la route publique `GET /api/client-config` (`{ sentry_dsn, environment, release }`) et ne démarre Sentry que si `sentry_dsn` est défini. Un DSN est public par nature : il permet seulement d'envoyer des événements au projet.

Une erreur levée avant la réponse de `/api/client-config` n'est pas envoyée.

## 4. Sourcemaps

Le JavaScript servi est minifié ; pour afficher des piles d'appels lisibles, Sentry a besoin des sourcemaps du build exact.

- `vite.config.ts` active `build.sourcemap: 'hidden'` et `@sentry/vite-plugin` **seulement quand `SENTRY_AUTH_TOKEN` est défini**. Le plugin envoie les fichiers pour la version `SENTRY_RELEASE`, puis supprime les `.map` de `dist/` : ils ne sont jamais publiés.
- Le workflow `Bundle` construit une fois par version et transmet `SENTRY_AUTH_TOKEN` (secret), `SENTRY_ORG`, `SENTRY_PROJECT` (variables du dépôt) et `SENTRY_RELEASE` (la version du bundle, la même qu'`APP_RELEASE`).
- Sans le token (local, CI), le build est inchangé et n'a pas de sourcemaps.

## 5. Configurer Sentry

1. Créer l'organisation dans la **région UE** (sentry.io, données stockées en Allemagne), offre _Developer_ (gratuite).
2. Créer un projet **React** (le navigateur et le backend le partagent ; l'environnement distingue le staging de la production).
3. _Settings → Security & Privacy_ : activer **Prevent Storing of IP Addresses** ; laisser _Data Scrubber_ activé.
4. _Alerts_ : une alerte e-mail à chaque nouvelle issue.
5. Copier le DSN (_Settings → Client Keys_) dans la variable `SENTRY_DSN` des environnements GitHub `staging` et `production`, et régler `SENTRY_ENVIRONMENT` sur `staging` ou `production` ([guide du déploiement](deployment.fr.md)).
6. Créer un token d'organisation (_Settings → Auth Tokens_ ; ces tokens peuvent créer des versions et envoyer les sourcemaps), en secret **du dépôt** `SENTRY_AUTH_TOKEN`, et les variables du dépôt `SENTRY_ORG` (identifiant de l'organisation) et `SENTRY_PROJECT` (identifiant du projet).

La conservation de l'offre gratuite est de 30 jours (90 jours sur les offres payantes), comme l'écrit la politique de confidentialité : changer d'offre ou de durée impose de mettre la politique à jour (`privacy.retention.errorReports`).

## 6. Vérifier que ça marche

- En local : mettre un DSN dans `backend/.env`, lancer le backend et le frontend, arrêter PostgreSQL (`docker compose stop db`) et appeler `/api/health/db` : l'erreur `Échec de la connexion à la base de données` apparaît dans Sentry, environnement `local`.
- Après un déploiement : `GET /api/client-config` sur le domaine renvoie le DSN, l'environnement et la version ; une erreur provoquée dans l'application apparaît dans Sentry avec cette version, et sa pile d'appels pointe vers les fichiers sources (`src/...`).

## 7. Tests

`backend/tests/test_monitoring.py`, `frontend/src/monitoring/sentry.test.ts`, et les cas Sentry de `ErrorBoundary.test.tsx` et `queryClient.test.ts` : voir le [guide des tests](testing.fr.md). Ils utilisent un transport en mémoire ou `beforeSend` : aucun événement ne quitte la machine.
