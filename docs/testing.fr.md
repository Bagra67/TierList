# Guide des tests

[English](testing.md) | Français

Ce guide explique le fonctionnement des tests de TierList : les outils utilisés, ce que fait chaque test, son but et le résultat attendu.

|               | Backend                                              | Frontend                                        |
| ------------- | ---------------------------------------------------- | ----------------------------------------------- |
| Outil de test | [pytest](https://docs.pytest.org/)                   | [Vitest](https://vitest.dev/)                   |
| Compléments   | `TestClient` de FastAPI, fixtures pytest, pytest-cov | Testing Library, jsdom, jest-dom, couverture v8 |
| Emplacement   | `backend/tests/`                                     | à côté du code : `frontend/src/**/*.test.tsx`   |
| Lancer        | `uv run pytest` (dans `backend/`)                    | `pnpm test` (dans `frontend/`)                  |
| Couverture    | `uv run pytest --cov=app`                            | `pnpm test:coverage`                            |

Les deux suites de tests tournent aussi sur **chaque pull request** dans la CI (`.github/workflows/ci.yml`). Une PR ne peut pas être fusionnée dans `develop` ou `main` tant qu'un test échoue.

---

## 1. Backend (pytest)

### 1.1 Fonctionnement de pytest

- **Découverte** : pytest cherche dans `tests/` (configuré dans `pyproject.toml`) les fichiers nommés `test_*.py`, et exécute chaque fonction nommée `test_*` qu'ils contiennent.
- **Assertions** : un test est une simple fonction qui utilise `assert`. Si un `assert` échoue ou si une exception est levée, le test **échoue**, et pytest affiche les valeurs comparées.
- **Fixtures** : une préparation réutilisable, passée au test via ses paramètres. Par exemple, `def test_x(client)` reçoit la fixture `client`. Une fixture peut exécuter du nettoyage après le test (la partie après `yield`). Sa _portée_ (_scope_) indique à quelle fréquence elle est créée : à chaque test (par défaut) ou une seule fois par exécution (`scope="session"`).
- **Fixtures intégrées utilisées ici** :
  - `monkeypatch` modifie des variables d'environnement ou le dossier courant, pour un seul test ;
  - `tmp_path` fournit un dossier temporaire vide ;
  - `capsys` capture ce qui est écrit sur stdout/stderr.
- **Marqueurs** : des étiquettes sur les tests. `integration` marque les tests qui ont besoin d'un vrai PostgreSQL : on peut les sélectionner avec `-m integration` ou les exclure avec `-m "not integration"`.
- **`TestClient` de FastAPI** : envoie des requêtes HTTP à l'application **en mémoire**, sans démarrer de serveur. Par exemple, `client.get("/hello")` renvoie une réponse dont on vérifie le `status_code` et le `json()`.
- **`app.dependency_overrides`** : remplace une dépendance FastAPI pendant un test. Les tests remplacent `get_db_session`, la dépendance qui fournit la session de base de données, pour simuler une base qui fonctionne ou qui est en panne.

### 1.2 Lancer les tests

| Commande (dans `backend/`)                                             | Effet                                                   |
| ---------------------------------------------------------------------- | ------------------------------------------------------- |
| `uv run pytest`                                                        | Tous les tests                                          |
| `uv run pytest -v`                                                     | Une ligne par test, avec son nom et son résultat        |
| `uv run pytest -m "not integration"`                                   | Tests unitaires seulement (pas besoin de base)          |
| `uv run pytest -m integration`                                         | Tests d'intégration seulement (base nécessaire)         |
| `uv run pytest --cov=app`                                              | Tous les tests, plus un tableau de couverture de `app/` |
| `uv run pytest tests/test_logging.py::test_log_level_defaults_to_info` | Un seul test                                            |

Les tests d'intégration ont besoin que PostgreSQL tourne : `docker compose up -d --wait` depuis la racine du dépôt.

### 1.3 Tests unitaires : `tests/test_main.py` (routes de l'API)

Ces tests appellent l'API avec `TestClient`. Ils n'ont jamais besoin d'une vraie base de données.

| Test                         | Ce qu'il fait                                                                                                                                 | But                                                                                 | Résultat attendu                                       |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `test_hello`                 | Appelle `GET /hello`.                                                                                                                         | Vérifier la route affichée par le frontend.                                         | `200` et `{"message": "Hello World"}`.                 |
| `test_health`                | Appelle `GET /health` sans remplacer aucune dépendance.                                                                                       | La sonde de vie doit répondre sans la base.                                         | `200` et `{"status": "ok"}`.                           |
| `test_health_db_ok`          | Remplace la session de base par une session sur une base **SQLite en mémoire**, puis appelle `GET /health/db`.                                | Vérifier le cas nominal du contrôle de la base, sans PostgreSQL.                    | `200` et `{"status": "ok"}`.                           |
| `test_health_db_unavailable` | Remplace la session par un faux objet dont `execute` lève une `OperationalError`, l'erreur que SQLAlchemy lève quand la base est injoignable. | Vérifier qu'une panne de base devient une erreur d'API propre, sans détail interne. | `503` et `{"detail": "Base de données indisponible"}`. |

La fixture `clear_dependency_overrides` s'exécute automatiquement après chaque test (`autouse=True`) et retire les remplacements : les tests ne s'influencent jamais entre eux.

### 1.4 Tests unitaires : `tests/test_logging.py` (logs)

| Test                                                 | Ce qu'il fait                                                                                            | But                                                                                                           | Résultat attendu                                                                                                 |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `test_log_level_defaults_to_info`                    | Supprime `LOG_LEVEL`, puis lit la configuration des logs.                                                | Vérifier le niveau par défaut.                                                                                | `log_level == "INFO"`.                                                                                           |
| `test_log_level_is_case_insensitive`                 | Définit `LOG_LEVEL=debug`.                                                                               | On doit pouvoir écrire le niveau en minuscules.                                                               | `log_level == "DEBUG"`.                                                                                          |
| `test_invalid_log_level_is_rejected`                 | Définit `LOG_LEVEL=LOUD`.                                                                                | Une faute de frappe doit être détectée au lieu d'être ignorée silencieusement.                                | Une `ValidationError` est levée.                                                                                 |
| `test_app_logs_use_uvicorn_format_and_respect_level` | Règle le niveau sur `WARNING`, écrit un log `info` et un log `warning`, et capture stderr avec `capsys`. | Vérifier le filtrage par niveau et le format de sortie.                                                       | Le message `info` est absent ; la sortie contient `WARNING:` et `app.example - visible message`.                 |
| `test_database_failure_is_logged_with_traceback`     | Simule une base injoignable, appelle `GET /health/db` et capture stderr.                                 | Une panne de base doit être visible dans les logs du serveur, avec le détail de l'erreur, pour le diagnostic. | `503` ; stderr contient `ERROR:`, `app.main - Échec de la connexion à la base de données` et `OperationalError`. |

Deux fixtures rendent ces tests indépendants :

- `no_env_file` place le test dans un dossier temporaire vide (`tmp_path`). Votre `.env` local n'est donc jamais lu, et seules les variables définies par le test comptent.
- `restore_default_logging` s'exécute après chaque test : elle remet la configuration des logs sur `INFO` et retire les remplacements de dépendances.

### 1.5 Tests d'intégration : `tests/integration/` (vrai PostgreSQL)

Ces tests vérifient ce que les faux objets ne peuvent pas vérifier : la vraie connexion, le vrai SQL et les migrations Alembic. Ils portent le marqueur `integration`.

Les fixtures de `tests/integration/conftest.py` préparent la base par étapes. Chaque étape s'appuie sur la précédente :

| Fixture             | Portée                 | Ce qu'elle fait                                                                                                                                                                                                                                    |
| ------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_database_url` | une fois par exécution | Lit la configuration PostgreSQL, se connecte au serveur et crée la base **`<POSTGRES_DB>_test`** (ex. `tierlist_test`) si elle n'existe pas. Les données de développement ne sont **jamais touchées**.                                             |
| `migrated_engine`   | une fois par exécution | Applique les migrations Alembic (`upgrade head`) sur la base de test, puis fournit un moteur de connexion.                                                                                                                                         |
| `db_session`        | à chaque test          | Ouvre une transaction et donne au test une session à l'intérieur. À la fin du test, la transaction est **annulée** (_rollback_) : rien de ce que le test a écrit ne subsiste, et chaque test part d'une base propre.                               |
| `client`            | à chaque test          | Un `TestClient` dont la dépendance de base de données utilise `db_session`.                                                                                                                                                                        |
| `auth_client`       | à chaque test          | `client` avec une configuration adaptée à `TestClient` : cookie de refresh non `Secure` et sur le chemin `/auth`. `TestClient` parle en HTTP simple à `http://testserver/auth/...`, sans le proxy `/api`, et ne renverrait sinon jamais le cookie. |

| Test                                   | Ce qu'il fait                                           | But                                                                               | Résultat attendu             |
| -------------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------- |
| `test_health_db_against_real_postgres` | Appelle `GET /health/db` avec la vraie session de base. | Vérifier toute la chaîne : configuration, SQLAlchemy, driver psycopg, PostgreSQL. | `200` et `{"status": "ok"}`. |

#### `tests/integration/test_auth.py` (authentification)

Ces tests passent par les vraies routes, le service, les repositories et les migrations, avec la fixture `auth_client`. Aides communes : `register` (crée Alice et renvoie son access token) et `bearer` (l'en-tête `Authorization`).

| Test                                                                     | Ce qu'il fait                                                                                                                                     | But                                                                    | Résultat attendu                                                                                                                                                                    |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_register_creates_the_account_and_returns_tokens`                   | Inscrit `Alice@Example.com`, puis lit les tables `users` et `refresh_tokens`.                                                                     | Vérifier le cas nominal et ce qui est enregistré.                      | `201`, `token_type` `bearer`, `expires_in` `900`, un cookie `refresh_token` ; email enregistré en minuscules, mot de passe haché, seul le hash SHA-256 du refresh token est stocké. |
| `test_register_rejects_an_email_already_used_whatever_its_case`          | S'inscrit deux fois, la seconde avec `ALICE@example.COM`.                                                                                         | Les emails sont uniques quelle que soit la casse.                      | `409` et `{"detail": "Cet email est déjà utilisé"}`.                                                                                                                                |
| `test_register_validates_its_input` (3 cas)                              | Envoie un email invalide, un mot de passe de moins de 8 caractères ou un nom affiché vide.                                                        | Chaque champ est validé par l'API.                                     | `422`, avec seulement le champ fautif (`body.<champ>`) dans `errors`.                                                                                                               |
| `test_me_returns_the_authenticated_user`                                 | Appelle `GET /auth/me` avec l'access token de l'inscription.                                                                                      | Vérifier l'authentification Bearer.                                    | `200`, email et nom affiché ; pas de `password_hash` dans le corps.                                                                                                                 |
| `test_me_requires_a_valid_access_token` (2 cas)                          | Appelle `GET /auth/me` sans token, puis avec `not-a-jwt`.                                                                                         | Une route protégée refuse les appels anonymes.                         | `401`, `{"detail": "Authentification requise"}` et `WWW-Authenticate: Bearer`.                                                                                                      |
| `test_login_with_valid_credentials`                                      | S'inscrit, vide les cookies, puis se connecte avec l'email dans une autre casse.                                                                  | Vérifier la connexion.                                                 | `200`, nouveau cookie `refresh_token`, et l'access token ouvre `GET /auth/me`.                                                                                                      |
| `test_login_failures_are_indistinguishable` (2 cas)                      | Se connecte avec un mot de passe faux, puis avec un email inconnu.                                                                                | La réponse ne doit pas révéler quels emails ont un compte.             | `401` et le même `{"detail": "Email ou mot de passe incorrect"}` dans les deux cas.                                                                                                 |
| `test_refresh_rotates_the_refresh_token`                                 | Appelle `POST /auth/refresh` avec le cookie de l'inscription.                                                                                     | Vérifier la rotation.                                                  | `200`, un cookie `refresh_token` différent, et le nouvel access token fonctionne.                                                                                                   |
| `test_replaying_a_rotated_refresh_token_revokes_the_whole_family`        | Rafraîchit une fois, puis présente de nouveau le premier token (déjà remplacé), puis le plus récent.                                              | Détection de vol : un token rejoué révoque toute la session.           | Le rejeu reçoit `401` avec `Session expirée, veuillez vous reconnecter`, et le token le plus récent est refusé lui aussi (`401`).                                                   |
| `test_expired_refresh_token_is_rejected`                                 | Place le `expires_at` du token enregistré dans le passé, puis rafraîchit.                                                                         | Un token expiré est inutilisable.                                      | `401`.                                                                                                                                                                              |
| `test_unknown_refresh_token_is_rejected_and_clears_the_cookie`           | Rafraîchit avec un cookie qui ne correspond à aucun token.                                                                                        | Le navigateur ne doit pas garder un cookie inutile.                    | `401`, et `Set-Cookie` vide le cookie (`Max-Age=0`).                                                                                                                                |
| `test_refresh_without_cookie_is_rejected`                                | Rafraîchit sans aucun cookie.                                                                                                                     | Pas de session sans cookie.                                            | `401`.                                                                                                                                                                              |
| `test_logout_revokes_the_session`                                        | Se déconnecte, puis tente de rafraîchir avec l'ancien cookie.                                                                                     | La déconnexion ferme la session côté serveur.                          | `204`, cookie retiré, puis `401` au rafraîchissement.                                                                                                                               |
| `test_logout_without_session_succeeds`                                   | Se déconnecte sans cookie.                                                                                                                        | La déconnexion n'échoue jamais.                                        | `204`.                                                                                                                                                                              |
| `test_refresh_cookie_attributes`                                         | S'inscrit avec la configuration de cookie de production et lit `Set-Cookie`.                                                                      | Vérifier les protections du cookie.                                    | `HttpOnly`, `Secure`, `SameSite=strict`, `Path=/api/auth` et `Max-Age=2592000` (30 jours).                                                                                          |
| `test_delete_account_removes_the_user_and_its_sessions`                  | S'inscrit, puis appelle `DELETE /auth/me` avec le mot de passe ; lit les tables, puis tente `GET /auth/me`, un rafraîchissement et une connexion. | La suppression est définitive et met fin à toutes les sessions.        | `204`, cookie retiré, `users` et `refresh_tokens` vides ; puis `401` pour `GET /auth/me`, le rafraîchissement et la connexion.                                                      |
| `test_delete_account_requires_the_right_password`                        | Supprime avec un mot de passe faux.                                                                                                               | Un access token volé ne suffit pas pour supprimer le compte.           | `403`, `{"detail": "Mot de passe incorrect"}` ; l'utilisateur existe toujours.                                                                                                      |
| `test_delete_account_requires_an_access_token`                           | Supprime sans l'en-tête `Authorization`.                                                                                                          | Seul un utilisateur authentifié peut supprimer son compte.             | `401`.                                                                                                                                                                              |
| `test_delete_account_without_password_is_refused_for_a_password_account` | Supprime avec un corps vide un compte qui a un mot de passe.                                                                                      | Seuls les comptes créés avec Google peuvent se passer du mot de passe. | `403` et `{"detail": "Mot de passe incorrect"}`.                                                                                                                                    |

#### `tests/integration/test_google_auth.py` (connexion avec Google)

La fixture `google` est un `FakeGoogleOAuthClient` : le vrai client Google (URL d'autorisation comprise) sauf `fetch_identity`, qui renvoie l'identité choisie par le test (`ALICE_GOOGLE` par défaut) ou lève `GoogleAuthError` ; il n'appelle jamais Google. `google_client` l'installe à la place de `get_google_oauth_client`, par-dessus `auth_client`. Aides : `start_google_login` (renvoie le `state` envoyé à Google), `google_callback`, `sign_in_with_google` et `current_user` (rafraîchissement puis `GET /auth/me`).

| Test                                                                          | Ce qu'il fait                                                                 | But                                                                      | Résultat attendu                                                                                                                                                                                   |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_login_redirects_to_google_with_a_signed_attempt_cookie`                 | Appelle `GET /auth/google/login`.                                             | Vérifier le départ du flux.                                              | `302` vers `https://accounts.google.com/` ; cookie `google_login` `HttpOnly`, `SameSite=lax`, `Path=/auth/google`, `Max-Age=600`.                                                                  |
| `test_first_google_sign_in_creates_an_account_without_password`               | Flux complet avec une nouvelle identité Google.                               | Vérifier la création du compte.                                          | `302` vers `/` ; le faux client a reçu le code ; utilisateur `alice@gmail.com` (minuscules), nom `Alice Martin`, `has_password` faux ; une ligne `oauth_accounts` `google` / `google-subject-123`. |
| `test_next_google_sign_in_reuses_the_same_account`                            | Se connecte deux fois, la seconde avec un autre email pour le même `sub`.     | Le compte est retrouvé par l'identifiant Google stable, pas par l'email. | Un seul utilisateur, toujours `alice@gmail.com`.                                                                                                                                                   |
| `test_google_identity_is_linked_to_an_existing_account_with_a_verified_email` | Inscrit `alice@gmail.com` avec un mot de passe, puis se connecte avec Google. | Règle de liaison pour un email vérifié.                                  | Le même compte (`display_name` `Alice`, `has_password` vrai) a maintenant l'identité Google.                                                                                                       |
| `test_unverified_google_email_is_refused` (2 cas)                             | `email_verified` faux, avec ou sans compte existant pour cet email.           | Un email non vérifié ne peut ni prendre un compte ni en créer un.        | `302` vers `/login?error=google_email_not_verified`, aucune session, aucune identité enregistrée.                                                                                                  |
| `test_callback_with_another_state_is_refused`                                 | Revient avec un `state` différent de celui du cookie.                         | Protection CSRF.                                                         | `302` vers `/login?error=google_failed`, aucune session.                                                                                                                                           |
| `test_callback_without_attempt_cookie_is_refused`                             | Revient sans le cookie `google_login`.                                        | Un retour que ce navigateur n'a pas lancé est refusé.                    | `302` vers `/login?error=google_failed`.                                                                                                                                                           |
| `test_callback_with_an_invalid_id_token_is_refused`                           | Le faux client lève `GoogleAuthError`.                                        | Une réponse de Google invalide n'ouvre jamais de session.                | `302` vers `/login?error=google_failed` ; le cookie `google_login` est effacé.                                                                                                                     |
| `test_error_returned_by_google_is_reported` (2 cas)                           | Google renvoie `error=access_denied` ou `error=server_error`.                 | L'utilisateur sait s'il a annulé ou si quelque chose a échoué.           | `/login?error=google_cancelled` ou `/login?error=google_failed`.                                                                                                                                   |
| `test_google_sign_in_is_unavailable_when_not_configured`                      | `get_google_oauth_client` renvoie `None` ; appelle les deux routes.           | L'application fonctionne sans identifiants Google.                       | Les deux redirigent vers `/login?error=google_unavailable`.                                                                                                                                        |
| `test_sign_in_can_resume_the_account_deletion`                                | Démarre avec `?next=delete-account`.                                          | Reconnexion avant de supprimer un compte Google.                         | `302` vers `/?confirm=delete-account`.                                                                                                                                                             |
| `test_unknown_next_step_is_rejected`                                          | Démarre avec `?next=https://evil.example.com`.                                | Pas de redirection ouverte.                                              | `422`.                                                                                                                                                                                             |
| `test_password_sign_in_is_refused_for_a_google_only_account`                  | Se connecte par mot de passe sur un compte créé avec Google.                  | Un tel compte n'a pas de mot de passe.                                   | `401`.                                                                                                                                                                                             |
| `test_google_only_account_is_deleted_after_a_recent_sign_in`                  | Supprime avec un access token dont l'`auth_time` date d'1 minute, corps vide. | Une connexion récente confirme la suppression.                           | `204` ; `users` et `oauth_accounts` vides.                                                                                                                                                         |
| `test_google_only_account_deletion_requires_a_recent_sign_in`                 | Idem avec un `auth_time` de 10 minutes.                                       | Une ancienne session seule ne suffit pas pour supprimer le compte.       | `403` avec `Reconnectez-vous avec Google pour confirmer la suppression` ; l'utilisateur existe toujours.                                                                                           |

**Quand PostgreSQL n'est pas disponible :**

- **En local**, les tests d'intégration sont **ignorés** (_skipped_), avec le message `PostgreSQL is not reachable: start it with docker compose up -d --wait`. Les autres tests tournent quand même.
- **En CI** (`CI=true`), ils **échouent** : une base absente y est un vrai problème, qui ne doit pas être masqué.

### 1.6 Test de contrat : `tests/test_openapi.py` (contrat d'API)

| Test                                | Ce qu'il fait                                                                                                                                                        | But                                                                                                            | Résultat attendu                                                                                                      |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `test_openapi_schema_is_up_to_date` | Construit le schéma OpenAPI à partir de l'application (`render_openapi()` dans `scripts/export_openapi.py`) et le compare au fichier commité `backend/openapi.json`. | Le frontend génère ses types TypeScript à partir de ce fichier : il doit toujours correspondre à la vraie API. | Identiques. Sinon le test échoue et indique de lancer `uv run python scripts/export_openapi.py`, puis `pnpm gen:api`. |

Côté frontend, l'étape CI **Check API types are up to date** régénère `src/api/schema.d.ts` et échoue s'il diffère du fichier commité. Un changement de contrat qui casse le frontend fait échouer `pnpm typecheck`, y compris dans les simulations des tests.

### 1.7 Tests unitaires : `tests/test_errors.py` (format d'erreur)

Ces tests utilisent une petite application FastAPI dédiée, avec `register_error_handlers` et trois routes de test : les ajouter à `app.main` modifierait le contrat d'API. Son `TestClient` est créé avec `raise_server_exceptions=False` pour qu'une exception devienne une réponse, comme sur un vrai serveur.

| Test                                              | Ce qu'il fait                                                                          | But                                                                                                                 | Résultat attendu                                                                                                                                                  |
| ------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_unexpected_error_returns_generic_500`       | Appelle une route qui lève `RuntimeError("secret internal detail")` et capture stderr. | Une erreur imprévue ne doit pas exposer de détail interne au client, mais doit être journalisée pour le diagnostic. | `500` avec `{"detail": "Erreur interne du serveur"}`, sans le message de l'exception ; stderr contient `ERROR:`, `Erreur non gérée sur GET /boom` et l'exception. |
| `test_validation_error_lists_invalid_fields`      | Appelle `/items/abc` (`item_id` non entier, `limit` manquant).                         | Vérifier le format 422 sur lequel s'appuie le frontend.                                                             | `422`, `detail` vaut `Requête invalide`, `errors` liste `path.item_id` et `query.limit`, chacun avec un message.                                                  |
| `test_http_exception_keeps_its_status_and_detail` | Appelle une route qui lève `HTTPException(404, "Introuvable")`.                        | Les erreurs prévues gardent leur statut et leur message.                                                            | `404` avec `{"detail": "Introuvable"}`.                                                                                                                           |

### 1.8 Test unitaire : `tests/test_versions.py` (version)

| Test                        | Ce qu'il fait                                                                                            | But                                                                                                    | Résultat attendu               |
| --------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------ |
| `test_versions_are_in_sync` | Lit la version de `backend/pyproject.toml` et de `frontend/package.json` et les compare à `app.version`. | Le dépôt a une seule version ([guide des releases](releasing.fr.md)) ; le workflow `Release` la tague. | Les trois valeurs sont égales. |

### 1.9 Tests unitaires : `tests/test_security.py` (primitives d'authentification)

Tests des fonctions pures de `app/core/security.py`, avec une clé de signature de test : ni base de données, ni configuration.

| Test                                                          | Ce qu'il fait                                                                                                                             | But                                                             | Résultat attendu                                                                    |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `test_password_hash_verifies_only_the_original_password`      | Hache un mot de passe, puis le vérifie, ainsi qu'un mauvais.                                                                              | Vérifier le hachage Argon2id.                                   | Le hash diffère du mot de passe ; seul le mot de passe d'origine est accepté.       |
| `test_access_token_round_trip`                                | Crée un access token, puis le décode.                                                                                                     | Vérifier les claims.                                            | Même identifiant d'utilisateur et même `auth_time`.                                 |
| `test_expired_access_token_is_rejected`                       | Crée un token émis il y a une heure, valable 15 minutes.                                                                                  | Un token expiré est refusé.                                     | `InvalidAccessTokenError`.                                                          |
| `test_access_token_signed_with_another_key_is_rejected`       | Signe avec une autre clé.                                                                                                                 | Un token forgé est refusé.                                      | `InvalidAccessTokenError`.                                                          |
| `test_invalid_access_tokens_are_rejected` (4 cas)             | Décode un token de type `refresh`, un token dont le `sub` n'est pas un UUID, un token sans expiration et une chaîne qui n'est pas un JWT. | Tout token mal formé est refusé.                                | `InvalidAccessTokenError` à chaque fois.                                            |
| `test_unsigned_access_token_is_rejected`                      | Décode un token non signé `alg: none`.                                                                                                    | Attaque classique contre les bibliothèques JWT.                 | `InvalidAccessTokenError`.                                                          |
| `test_refresh_tokens_are_random_and_hashed_deterministically` | Génère deux refresh tokens et les hache.                                                                                                  | Le hash stocké doit être reproductible pour retrouver le token. | Deux tokens différents ; même hash pour un même token ; 64 caractères hexadécimaux. |

### 1.10 Tests unitaires : `tests/test_google_oauth.py` (client Google)

Aucun appel réseau : une paire de clés RSA générée pour les tests joue le rôle des clés de signature de Google (`StaticJWKClient` renvoie sa clé publique au lieu de télécharger le JWKS), et un `httpx.MockTransport` remplace le point d'échange de Google.

| Test                                                               | Ce qu'il fait                                                                                                          | But                                                                                             | Résultat attendu                                                                                                                                                                                 |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `test_login_attempt_round_trips_through_its_signed_cookie`         | Écrit une tentative dans la valeur de son cookie, puis la relit.                                                       | Le state, le nonce, le vérificateur et l'étape suivante survivent à l'aller-retour chez Google. | La même tentative ; `matches_state` n'accepte que son state.                                                                                                                                     |
| `test_login_attempt_cookie_signed_with_another_key_is_rejected`    | Lit un cookie signé avec une autre clé.                                                                                | Le navigateur ne peut pas forger une tentative.                                                 | `GoogleAuthError`.                                                                                                                                                                               |
| `test_code_challenge_is_the_s256_hash_of_the_verifier`             | Reprend l'exemple de la RFC 7636.                                                                                      | Vérifier PKCE S256.                                                                             | `E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM`.                                                                                                                                                   |
| `test_authorization_url_asks_for_openid_with_pkce`                 | Construit l'URL d'autorisation.                                                                                        | Vérifier chaque paramètre envoyé à Google.                                                      | L'URL de Google avec `client_id`, `redirect_uri`, `response_type=code`, `scope=openid email profile`, `state`, `nonce`, `code_challenge`, `code_challenge_method=S256`, `prompt=select_account`. |
| `test_fetch_identity_exchanges_the_code_and_verifies_the_id_token` | Le faux point d'échange renvoie un `id_token` valide.                                                                  | Vérifier l'échange et le résultat.                                                              | La `GoogleIdentity` attendue ; le formulaire envoyé contient le code, l'ID et le secret client, l'URI de redirection, le `grant_type` et le vérificateur.                                        |
| `test_invalid_id_tokens_are_rejected` (6 cas)                      | `id_token` avec une autre audience, un autre émetteur, un autre nonce, expiré, signé par une autre clé, ou sans email. | Seul un token émis par Google, pour cette application et cette tentative, est accepté.          | `GoogleAuthError` à chaque fois.                                                                                                                                                                 |
| `test_token_endpoint_failures_are_reported` (3 cas)                | Le point d'échange répond `400`, un corps sans `id_token`, ou du non-JSON.                                             | Les échecs de Google deviennent une erreur propre.                                              | `GoogleAuthError` à chaque fois.                                                                                                                                                                 |

---

## 2. Frontend (Vitest)

### 2.1 Fonctionnement de Vitest

- **Découverte** : Vitest exécute chaque fichier `*.test.ts` / `*.test.tsx`. Il est configuré dans le bloc `test` de `vite.config.ts`.
- **Structure** :
  - `describe('App', …)` regroupe des tests liés ;
  - `it('…', …)` est un test ;
  - `expect(valeur).toBe…()` est une assertion, et le test échoue si elle n'est pas vérifiée.
- **jsdom** : un navigateur simulé dans Node.js. On peut afficher et inspecter des composants sans ouvrir de vrai navigateur.
- **Testing Library** :
  - `render(<App />)` affiche le composant ;
  - `screen` cherche dans la page **comme un utilisateur la voit** : par texte visible (`getByText`) ou par rôle d'accessibilité (`getByRole('heading')`, `findByRole('alert')`) ;
  - `getBy…` cherche immédiatement, tandis que `findBy…` **attend** que l'élément apparaisse, ce qui est utile après un appel asynchrone.
- **jest-dom** : ajoute des assertions lisibles comme `toBeInTheDocument()` et `toHaveTextContent()`. Il est chargé par `src/test/setup.ts`, qui démonte aussi les composants après chaque test.
- **Simulations** (`vi.fn`, `vi.stubGlobal`, `vi.spyOn`) : remplacent une fonction par une version factice dont le test décide le comportement. Ici, le `fetch` global est remplacé par `vi.stubGlobal('fetch', …)` et restauré par `vi.unstubAllGlobals()` après chaque test : les tests **n'appellent jamais le vrai backend**. Ils sont donc rapides et ne dépendent d'aucun serveur lancé. Tout ce qui est au-dessus de `fetch` (client API, hooks TanStack Query, composants) tourne pour de vrai.
- **`renderWithQueryClient`** (`src/test/renderWithQueryClient.tsx`) : affiche un composant dans un client TanStack Query **neuf** pour chaque test, pour qu'aucune donnée en cache ne passe d'un test à l'autre. Les nouveaux essais sont désactivés (`retry: false`) pour que les cas d'erreur échouent tout de suite. À utiliser à la place de `render` pour tout composant qui charge des données.
- **`<dialog>` dans jsdom** : jsdom gère l'attribut `open` de `<dialog>` mais pas `showModal()` ni `close()` ; `src/test/setup.ts` en ajoute une version minimale (`close()` déclenche aussi l'événement `close`). Le piège du focus et la touche Échap, gérés par le navigateur, ne sont donc pas testables ici.
- **`stubBackend`** (`src/test/stubBackend.ts`) : remplace `fetch` par un faux backend décrit route par route (`'GET /auth/me': () => Response.json(alice)`) ; une route non déclarée répond `404`, pour qu'un appel inattendu fasse échouer le test. `calledRoutes` liste les appels reçus, et `alice`, `tokenResponse` et `unauthorized` sont des réponses toutes faites. Les tests qui passent par le client d'API appellent aussi `setAccessToken(null)` après chaque test, car l'access token est gardé en mémoire par `src/api/client.ts`.

### 2.2 Lancer les tests

| Commande (dans `frontend/`) | Effet                                                        |
| --------------------------- | ------------------------------------------------------------ |
| `pnpm test`                 | Lance tous les tests une fois                                |
| `pnpm test:watch`           | Relance les tests concernés à chaque modification de fichier |
| `pnpm test:coverage`        | Tous les tests, plus un tableau de couverture de `src/`      |

### 2.3 Tests : `src/App.test.tsx`

`App` (les routes) est affiché dans un `MemoryRouter` à un chemin donné, avec `renderWithQueryClient` et `stubBackend` : routeur, garde, hooks et client d'API s'exécutent tous.

| Test                                                | Ce qu'il fait                                                           | But                                                             | Résultat attendu                                          |
| --------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------- | --------------------------------------------------------- |
| `redirects to the login page without a session`     | Ouvre `/` ; `POST /auth/refresh` répond `401`.                          | Les pages privées exigent une session.                          | Le titre `Connexion` est affiché.                         |
| `restores the session and shows the home page`      | Ouvre `/` ; le rafraîchissement et `GET /auth/me` réussissent.          | Un cookie de refresh valide restaure la session au chargement.  | Le titre `Hello World` et `Connecté en tant que Alice`.   |
| `shows an alert when the backend cannot be reached` | Le rafraîchissement répond `502`. `console.error` est rendu silencieux. | Une panne du backend n'est pas confondue avec « non connecté ». | Une `alert` contenant `Impossible de joindre le backend`. |
| `logs out and goes back to the login page`          | Clique sur `Se déconnecter`.                                            | Vérifier la déconnexion.                                        | Le titre `Connexion` est affiché.                         |
| `redirects unknown pages to the home page`          | Ouvre `/does-not-exist` avec une session.                               | Un chemin inconnu n'affiche pas une page vide.                  | Le titre `Hello World`.                                   |

### 2.4 Tests : `src/api/hello.test.ts`

Tests de `getHello`, l'appel d'API lui-même, avec un `fetch` simulé.

| Test                                                                  | Ce qu'il fait                                                                                 | But                                                                                                                    | Résultat attendu                                                                              |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `calls GET /api/hello and returns the JSON body`                      | `fetch` répond `200` avec `{ message: 'Hello World' }` ; le test inspecte la requête envoyée. | Vérifier que le client commun vise la bonne URL (préfixe `/api`, redirigé par le proxy Vite) et renvoie le corps typé. | `{ message: 'Hello World' }` est renvoyé ; la requête est un `GET` sur `/api/hello`.          |
| `throws an ApiError carrying the status when the backend fails`       | `fetch` répond `500` avec `{ detail: 'boom' }` (format `ErrorResponse` du backend).           | Vérifier le contrat d'erreur : toute réponse hors 2xx devient une `ApiError` que l'appelant peut inspecter.            | Une `ApiError` avec `status: 500`, `body: { detail: 'boom' }` et `message: 'boom'` est levée. |
| `falls back to the HTTP status when the body is not an ErrorResponse` | `fetch` répond `502` avec un corps texte, comme le proxy Vite quand le backend est arrêté.    | L'erreur reste exploitable même quand le corps ne vient pas du backend.                                                | Une `ApiError` avec `status: 502` et `message: 'HTTP 502'` est levée.                         |

### 2.5 Tests : `src/pages/HomePage.test.tsx`

La page d'accueil avec une session restaurée ; seul `GET /hello` change d'un test à l'autre.

| Test                                                               | Ce qu'il fait                                                                | But                                                                               | Résultat attendu                                                                           |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `shows a loading message while the backend answers`                | `GET /hello` ne répond jamais.                                               | Vérifier l'état de chargement.                                                    | `Chargement…` est affiché.                                                                 |
| `shows the message returned by the backend and the connected user` | `GET /hello` répond `{ message: 'Hello World' }`.                            | Vérifier l'état de succès.                                                        | Le titre `Hello World` et `Connecté en tant que Alice`.                                    |
| `shows an alert when the backend cannot be reached`                | `GET /hello` répond `500` ; `console.error` est rendu silencieux et vérifié. | L'utilisateur est prévenu, et l'erreur est journalisée par le client de requêtes. | Une `alert` contenant `Impossible de joindre le backend`, et `console.error` a été appelé. |
| `reopens the account deletion after a Google sign-in`              | Ouvre `/?confirm=delete-account` avec une session.                           | Au retour de la reconnexion, l'utilisateur reprend la suppression.                | Le dialogue `Supprimer mon compte` est visible.                                            |

### 2.6 Tests : `src/pages/LoginPage.test.tsx` et `src/pages/RegisterPage.test.tsx`

Le formulaire est rempli avec `fireEvent.change` et envoyé avec `fireEvent.click` ; une route `/` affiche `Accueil` pour vérifier la redirection.

| Test                                                                     | Ce qu'il fait                                                          | But                                                           | Résultat attendu                                                                                  |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Connexion : `sends the credentials and opens the home page`              | Identifiants valides.                                                  | Vérifier le corps de la requête et la redirection.            | Le titre `Accueil` ; le corps de la requête est `{ email, password }`.                            |
| Connexion : `shows the backend message when the credentials are wrong`   | `POST /auth/login` répond `401`.                                       | L'utilisateur comprend pourquoi la connexion a échoué.        | Une `alert` avec `Email ou mot de passe incorrect` ; toujours sur la page de connexion.           |
| Connexion : `disables the button while the request is pending`           | `POST /auth/login` ne répond jamais.                                   | Empêcher les doubles envois.                                  | Un bouton `Connexion…` désactivé.                                                                 |
| Connexion : `shows validation errors next to the field`                  | `POST /auth/login` répond `422` sur `body.email`.                      | Les erreurs 422 s'affichent sur le bon champ.                 | Le message est affiché et le champ email a `aria-invalid="true"`.                                 |
| Inscription : `creates the account and opens the home page`              | Formulaire valide.                                                     | Vérifier le corps de la requête et la redirection.            | Le titre `Accueil` ; le corps est `{ email, password, display_name }`.                            |
| Inscription : `shows the backend message when the email is already used` | `POST /auth/register` répond `409`.                                    | Vérifier le message d'email en double.                        | Une `alert` avec `Cet email est déjà utilisé`.                                                    |
| Inscription : `shows validation errors next to the field`                | `POST /auth/register` répond `422` sur `body.password`.                | Les erreurs 422 s'affichent sur le bon champ.                 | Le message est affiché.                                                                           |
| Connexion : `links to the Google sign-in`                                | Affiche la page.                                                       | La connexion avec Google est proposée.                        | Un lien `Continuer avec Google` vers `/api/auth/google/login`.                                    |
| Connexion : `explains the Google error %s` (5 cas)                       | Ouvre `/login?error=<code>` pour chaque code connu et un code inconnu. | L'utilisateur comprend pourquoi la connexion Google a échoué. | Une `alert` avec le message correspondant ; un code inconnu affiche le message d'échec générique. |
| Inscription : `links to the Google sign-in`                              | Affiche la page.                                                       | L'inscription avec Google est proposée.                       | Un lien `Continuer avec Google` vers `/api/auth/google/login`.                                    |

### 2.7 Tests : `src/api/client.test.ts` (middleware d'authentification)

| Test                                                               | Ce qu'il fait                                                               | But                                                                                  | Résultat attendu                                                                                        |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `sends the access token in the Authorization header`               | `GET /auth/me` n'accepte que `Bearer token-1`.                              | Vérifier que le token en mémoire est envoyé.                                         | L'utilisateur est renvoyé.                                                                              |
| `refreshes an expired access token once, then retries the request` | Le token en mémoire est refusé ; le rafraîchissement en renvoie un nouveau. | Un token expiré est renouvelé sans que l'utilisateur s'en aperçoive.                 | Appels dans l'ordre : `GET /auth/me`, `POST /auth/refresh`, `GET /auth/me` ; l'utilisateur est renvoyé. |
| `shares a single refresh between concurrent requests`              | Deux requêtes simultanées avec un token expiré.                             | Deux rafraîchissements avec le même cookie ressembleraient à un vol pour le backend. | Un seul `POST /auth/refresh`.                                                                           |
| `returns the 401 when the session cannot be refreshed`             | `GET /auth/me` et le rafraîchissement répondent tous deux `401`.            | Pas de boucle infinie ; l'appelant voit la 401.                                      | Une `ApiError` avec `status: 401`.                                                                      |
| `never refreshes on a 401 from a session route such as login`      | `POST /auth/login` répond `401`.                                            | Un mot de passe faux ne doit pas déclencher de rafraîchissement.                     | Seul `POST /auth/login` est appelé ; son message est levé.                                              |
| `getFieldErrors` › `maps validation errors to body field names`    | Une `ApiError` 422 sur `body.email`.                                        | Les formulaires affichent les erreurs par champ.                                     | `{ email: '<message>' }`.                                                                               |
| `getFieldErrors` › `returns no field error for other errors`       | Une `ApiError` 500, puis `null`.                                            | Pas de fausse erreur de champ.                                                       | `{}` les deux fois.                                                                                     |

### 2.8 Tests : `src/api/auth.test.ts`

| Test                                                                             | Ce qu'il fait                                                                 | But                                                                                | Résultat attendu                                                                                                  |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `restores the session from the refresh cookie when no access token is in memory` | Le rafraîchissement et `GET /auth/me` réussissent.                            | Vérifier la restauration de session au chargement de la page.                      | L'utilisateur ; appels : rafraîchissement puis `GET /auth/me`.                                                    |
| `returns no user when there is no valid session`                                 | Le rafraîchissement répond `401`.                                             | « Non connecté » est un état normal, pas une erreur.                               | `null`, sans appeler `GET /auth/me`.                                                                              |
| `reports an unreachable backend instead of an anonymous user`                    | Le rafraîchissement répond `502`.                                             | Une panne du backend ne doit pas renvoyer l'utilisateur vers la page de connexion. | Une `ApiError` avec `status: 502`.                                                                                |
| `keeps the access token returned by login for the next requests`                 | Se connecte, puis appelle `GET /auth/me`, qui n'accepte que le nouveau token. | Le token de la connexion est utilisé ensuite.                                      | L'utilisateur est renvoyé.                                                                                        |
| `forgets the access token on logout, even if the backend fails`                  | `POST /auth/logout` répond `500`.                                             | La déconnexion locale doit toujours fonctionner.                                   | Une `ApiError` est levée, et la requête de déconnexion ne porte pas d'en-tête `Authorization`.                    |
| `forgets the access token once the account is deleted`                           | `DELETE /auth/me` répond `204`, puis la session est relue.                    | Après la suppression, aucune requête ne doit utiliser l'ancien token.              | `getCurrentUser()` renvoie `null` ; appels : `DELETE /auth/me` puis `POST /auth/refresh` (pas de `GET /auth/me`). |

### 2.9 Tests : `src/components/DeleteAccountDialog.test.tsx`

Le dialogue est affiché pour Alice (avec mot de passe, ou `googleOnlyAlice` sans) et avec une route `/login` qui montre `Connexion`, pour vérifier la redirection.

| Test                                                                   | Ce qu'il fait                                                   | But                                                              | Résultat attendu                                                                                                                                                                |
| ---------------------------------------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `keeps the confirmation dialog closed until asked`                     | Affiche, puis clique sur `Supprimer mon compte`.                | Rien n'est supprimé par erreur : la confirmation vient d'abord.  | Aucun dialogue au départ ; puis un dialogue visible nommé `Supprimer mon compte`.                                                                                               |
| `deletes the account with the password, then opens the login page`     | Confirme avec un mot de passe ; `DELETE /auth/me` répond `204`. | Vérifier la requête et la redirection.                           | Le titre `Connexion` ; un seul appel `DELETE /auth/me`, avec le corps `{ password }`.                                                                                           |
| `shows the backend message and stays open when the password is wrong`  | `DELETE /auth/me` répond `403`.                                 | L'utilisateur peut réessayer.                                    | Une `alert` avec `Mot de passe incorrect` ; le dialogue est toujours visible.                                                                                                   |
| `closes on cancel and forgets the previous error`                      | Après une `403`, clique sur `Annuler`, puis rouvre le dialogue. | Rouvrir repart d'un formulaire propre.                           | Le dialogue se ferme ; une fois rouvert, pas d'alerte (attendue avec `waitFor`, car TanStack Query notifie la remise à zéro de façon asynchrone) et un champ mot de passe vide. |
| `opens at once when resuming a deletion after a Google sign-in`        | Affiche avec `openOnMount` pour un compte Google.               | Au retour de Google, aucun clic supplémentaire n'est nécessaire. | Le dialogue est visible.                                                                                                                                                        |
| `deletes a Google account without asking for a password`               | Compte Google ; confirme ; `DELETE /auth/me` répond `204`.      | Un compte Google n'a pas de mot de passe à saisir.               | Pas de champ mot de passe ; le titre `Connexion` ; le corps de la requête est `{}`.                                                                                             |
| `offers to sign in again with Google when the last sign-in is too old` | Compte Google ; `DELETE /auth/me` répond `403`.                 | Expliquer comment confirmer.                                     | Une `alert` avec `Reconnectez-vous avec Google` et un lien `Se reconnecter avec Google` vers `/api/auth/google/login?next=delete-account`.                                      |

---

## 3. Lire les résultats

| Résultat            | Signification                                                                                                                                                                                            |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `passed` / ✓        | Le test s'est exécuté et toutes ses assertions sont vérifiées.                                                                                                                                           |
| `failed` / ✗        | Une assertion n'est pas vérifiée, ou une erreur inattendue a été levée. La sortie montre la valeur attendue et la valeur obtenue.                                                                        |
| `skipped` (backend) | Le test n'a pas été exécuté, avec la raison dans la sortie (`uv run pytest -rs` liste les raisons). Aujourd'hui, cela n'arrive que pour les tests d'intégration quand PostgreSQL ne tourne pas en local. |
| `error` (backend)   | Une fixture a échoué avant que le test puisse s'exécuter, par exemple pas de base en CI.                                                                                                                 |

**La couverture** indique, pour chaque fichier, la part du code exécutée par les tests :

- backend (pytest-cov) : `Stmts` (instructions), `Miss` (instructions qu'aucun test n'a exécutées) et `Cover` (pourcentage) ;
- frontend (Vitest) : `% Stmts` (instructions), `% Branch` (chemins `if`/`else`), `% Funcs` (fonctions), `% Lines` (lignes) et `Uncovered Line #s` (lignes qu'aucun test n'a exécutées).

Il n'y a pas de seuil minimal pour l'instant. La couverture aide à repérer le code non testé, mais elle ne prouve pas que les tests sont bons.

### 3.1 Rapport de tests en CI

Chaque exécution de la CI (GitHub → **Actions** → l'exécution → **Summary**) affiche, pour les jobs **Backend** et **Frontend** :

| Section          | Contenu                                                                                                                      |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| En-tête          | Verdict (✅ Passed / ❌ Failed) et totaux : tests, réussis, échoués, ignorés, durée totale.                                  |
| ❌ Failures      | Seulement si un test échoue : son nom, le message d'erreur et, dans un bloc dépliable, le détail de l'assertion et la trace. |
| ⏭️ Skipped       | Seulement si des tests sont ignorés : chaque test avec sa raison.                                                            |
| All tests        | Une ligne par test : statut, nom (`fichier::test` ou `fichier › describe > test`) et durée.                                  |
| 🐢 Slowest tests | Les 5 tests les plus lents, pour repérer ceux qui ralentissent. Affiché quand il y a plus de 5 tests.                        |
| Couverture       | Tableau de couverture (par fichier pour le backend, par métrique pour le frontend).                                          |

Le rapport est aussi produit **quand des tests échouent** : on lit la cause sans ouvrir les logs. Il est généré à partir des rapports JUnit XML de pytest (`--junitxml`) et de Vitest (reporter `junit`) par `.github/scripts/junit_summary.py`, qui n'utilise que la bibliothèque standard de Python.

Les rapports bruts (JUnit XML et couverture) sont joints à l'exécution comme **artefacts** (`backend-test-reports`, `frontend-test-reports`) pendant 14 jours.

---

## 4. Écrire un nouveau test

1. **Tester le comportement, pas l'implémentation** :
   - backend : vérifier le statut HTTP et le JSON renvoyé ;
   - frontend : vérifier ce que voit l'utilisateur, avec les textes et les rôles.
2. **Un test, un comportement**, avec un nom qui dit ce qui est attendu, par exemple `test_invalid_log_level_is_rejected`.
3. **Couvrir les cas d'erreur et les cas limites**, pas seulement le cas nominal.
4. **Garder les tests indépendants** : utiliser des fixtures et `dependency_overrides`, et nettoyer après le test (fixtures `autouse`, `vi.unstubAllGlobals`, `mockRestore`).
5. **Choisir le bon niveau** :
   - un test unitaire avec de faux objets pour la logique et le contrat d'API ;
   - un test d'intégration (`tests/integration/`, marqueur `integration`) dès que du vrai SQL ou des migrations entrent en jeu.
6. Placer les nouveaux tests frontend à côté du composant (`Composant.test.tsx`), et les nouveaux tests backend dans `backend/tests/`.
7. Lancer les tests en local avant de pousser ; la CI les relance sur la PR.
8. **Mettre à jour ce guide dans la même PR**, dans les deux langues (`testing.md` et `testing.fr.md`), dès qu'un test, une fixture ou un outil de test est ajouté, modifié ou supprimé (AGENTS.md §28).
