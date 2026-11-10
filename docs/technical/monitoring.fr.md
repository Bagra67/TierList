[English](monitoring.md) | Français

# Suivi des erreurs (Sentry)

Les erreurs de production, du backend comme du navigateur, sont envoyées à **Sentry**, qui les regroupe, garde leur pile d'appels et prévient par e-mail d'une nouvelle erreur. Rien n'est envoyé tant que `SENTRY_DSN` est vide (une valeur vide se lit comme pas de DSN, `/client-config` renvoie donc `null`) : le local, les tests et la CI n'envoient jamais rien.

Les logs eux-mêmes (INFO et au-dessus) ne vont toujours que dans la console du pod ([README du backend, Logs](../../backend/README.fr.md#10-logs)).

## 1. Ce qui est envoyé

| Source     | Envoyé                                                                                                                                                                                                                                                                                                      | Où dans le code                                                    |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Backend    | Chaque log `ERROR`, avec son exception : les loggers `app.*` de l'application (erreurs non gérées journalisées par `core/errors.py`, qui répond une 500 générique ; échecs des tâches de nuit), mais aussi uvicorn et les bibliothèques.                                                                    | `app/core/monitoring.py` (`LoggingIntegration(event_level=ERROR)`) |
| Navigateur | Plantages du rendu interceptés par la limite d'erreur, avec la pile de composants React.                                                                                                                                                                                                                    | `src/components/ErrorBoundary.tsx` (`componentDidCatch`)           |
| Navigateur | Requêtes en échec qui ne sont ni une réponse de l'API ni une connexion perdue : les erreurs du code. Une `ApiError` n'est pas envoyée (les 4xx attendues sont affichées par la page, les 5xx sont déjà envoyées par le backend), ni une `NetworkError` (`src/api/client.ts` y emballe un `fetch` en échec). | `src/api/queryClient.ts`                                           |
| Navigateur | Erreurs non interceptées et promesses rejetées (intégrations par défaut du SDK).                                                                                                                                                                                                                            | `src/monitoring/sentry.ts`                                         |

Chaque événement porte la **version** (`APP_RELEASE` : `vX.Y.Z` ou `develop-<commit>`) et l'**environnement** (`SENTRY_ENVIRONMENT` : `staging` ou `production`). Les avertissements ne sont pas envoyés, pour garder le quota gratuit pour les erreurs.

Une réponse 5xx du backend n'est pas un événement à elle seule : les intégrations FastAPI et Starlette du SDK ne capturent aucun code HTTP (`SENTRY_CAPTURED_RESPONSE_STATUS_CODES`, vide). Seul le log d'erreur écrit pour elle est envoyé, donc une panne donne une seule issue (par exemple, une base indisponible répond 503 et n'envoie que son log `Échec de la connexion à la base de données`).

## 2. Ce qui n'est pas envoyé

La politique de confidentialité promet des rapports d'erreur sans adresse IP, cookies ni contenu saisi. Le code le garantit :

- **Backend** (`configure_sentry`) : `send_default_pii=False` (ni IP de l'utilisateur, ni cookie), `max_request_body_size="never"` (aucun corps de requête : mots de passe, e-mails), `include_local_variables=False` (aucune variable des cadres de la pile), et `scrub_event` retire la query string de la requête (un `code` Google, un e-mail cherché par un modérateur), les cookies et tous les en-têtes sauf `User-Agent` (derrière Cloudflare, `Cf-Connecting-Ip` contient l'IP de l'utilisateur ; un `Referer` peut contenir un token de réinitialisation du mot de passe), et masque les segments secrets du chemin (voir plus bas) dans l'URL de la requête, le message du log et les valeurs des exceptions, ainsi que les adresses e-mail du message du log et des valeurs des exceptions (une ligne `DETAIL` de PostgreSQL peut en citer une). `scrub_breadcrumb` fait de même sur les breadcrumbs (URL sans query ni fragment, `http.query` et `http.fragment` retirés), et `scrub_transaction` sur les transactions et leurs spans si le tracing est activé (seule la description d'un span `http*` est coupée comme une URL ; une description SQL est seulement masquée, pour ne pas être coupée à un opérateur `?`). Le code de salle n'est écrit dans aucun log : les logs deviennent des fils d'Ariane. Le logger `uvicorn.access` est ignoré (`ignore_logger`) : chaque ligne d'accès contient l'IP du client et le chemin complet avec sa query. L'engine de la base a `hide_parameters=True` (`db/session.py`) : une erreur SQL ne recopie pas les valeurs de sa requête (e-mails, texte saisi) dans son message.
- **Navigateur** (`buildSentryOptions`) : depuis la v11 du SDK, `dataCollection` collecte par défaut ; `userInfo`, `cookies`, `httpHeaders`, `httpBodies` et `urlQueryParams` sont tous désactivés. `scrubEventUrl` et `scrubBreadcrumbUrls` retirent la query et le fragment de l'URL de l'événement et des breadcrumbs de navigation et de requête (le lien personnel d'invité porte son token dans le fragment : `/r/<code>#guest=…`), et masquent les segments secrets du chemin. Les breadcrumbs de la console sont désactivés (`withoutConsoleBreadcrumbs`) : un message de la console peut contenir une clé de requête, comme un e-mail cherché. Ni Session Replay, ni tracing.
- **Projet Sentry** : _Settings → Security & Privacy → Prevent Storing of IP Addresses_ doit être activé, sinon le serveur de Sentry enregistre l'adresse IP depuis laquelle le navigateur se connecte.

**Segments secrets du chemin** : le segment après `/results/`, `/rooms/` ou `/r/` (le token des résultats, le code de salle) donne accès à une partie. Des deux côtés, il devient `[Filtered]` (`SENTRY_SECRET_PATH_SEGMENT`) : `/api/results/[Filtered]`, `/r/[Filtered]`. Le reste du chemin est toujours envoyé. Dans un texte (message de log, valeur d'exception, message de fil d'Ariane), les paramètres `token` et `guest` d'un lien sont masqués aussi (`SENTRY_SECRET_LINK_PARAM`) : `?token=[Filtered]`, `#guest=[Filtered]`.

Le suivi des performances est désactivé (`SENTRY_TRACES_SAMPLE_RATE=0`) ; il peut être activé côté backend sans nouvelle version.

## 3. Comment le navigateur reçoit ses réglages

Un même build du frontend sert le staging et la production : le navigateur ne peut donc pas recevoir son DSN au build. La config (`{ sentry_dsn, environment, release }`) vient du backend à l'exécution :

- **Production** : le backend l'écrit dans l'`index.html` qu'il sert (`mount_frontend_after_api`, `app/core/frontend.py`), dans un élément `<script type="application/json" id="tierlist-client-config">` (non exécuté, `<` écrit `\u003c`). `main.tsx` appelle `initMonitoring()`, qui la lit et démarre Sentry avant le premier rendu : les erreurs du démarrage sont envoyées aussi. Un build sans `index.html` n'est pas servi (l'API démarre quand même), et un `index.html` sans `</head>` est servi sans l'élément ; les deux sont journalisés en erreur.
- **Développement** (Vite sert son propre `index.html`) : pas d'élément, donc `initMonitoring()` lit la route publique `GET /api/client-config` ; une erreur levée avant sa réponse n'est pas envoyée.

Sentry ne démarre que si `sentry_dsn` est défini. Un DSN est public par nature : il permet seulement d'envoyer des événements au projet.

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
- Après un déploiement : la source de la page contient l'élément `tierlist-client-config` avec le DSN, l'environnement et la version (renvoyés aussi par `GET /api/client-config`) ; une erreur provoquée dans l'application apparaît dans Sentry avec cette version, et sa pile d'appels pointe vers les fichiers sources (`src/...`).

## 7. Tests

`backend/tests/test_monitoring.py`, `frontend/src/monitoring/sentry.test.ts`, et les cas Sentry de `ErrorBoundary.test.tsx` et `queryClient.test.ts` : voir le [guide des tests](testing.fr.md). Ils utilisent un transport en mémoire ou `beforeSend` : aucun événement ne quitte la machine. `backend/tests/conftest.py` met aussi `SENTRY_DSN` à une chaîne vide avant l'import de `app.main`, pour qu'un DSN dans `backend/.env` ne serve jamais aux tests.
