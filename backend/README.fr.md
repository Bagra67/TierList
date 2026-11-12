# TierList — Backend FastAPI

[English](README.md) | Français

Backend Python basé sur [FastAPI](https://fastapi.tiangolo.com/), géré avec le gestionnaire de paquets et de projets [uv](https://docs.astral.sh/uv/).

> Ce dossier fait partie du dépôt [TierList](../README.fr.md). **Toutes les commandes ci-dessous se lancent depuis le dossier `backend/`** (`cd backend`).

---

## 1. Prérequis

- **uv** (il installe et gère lui-même Python si besoin)
- Python **3.15+**, celle des pods de production (fixée dans `.python-version`)

### Installer uv

**Windows (PowerShell)** :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux** :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Redémarrez ensuite votre terminal, puis vérifiez :

```bash
uv --version
```

---

## 2. Installer le projet

Depuis le dossier `backend/` :

```bash
uv sync
```

Cette commande :

- crée l'environnement virtuel `.venv/` s'il n'existe pas ;
- installe toutes les dépendances (y compris celles de dev) exactement aux versions du fichier `uv.lock`.

### Activer l'environnement virtuel (optionnel)

Avec `uv run`, l'activation n'est **pas nécessaire** : uv utilise automatiquement `.venv`.
Si vous voulez quand même l'activer (par ex. pour utiliser `python` ou `fastapi` directement) :

| Système              | Commande                     |
| -------------------- | ---------------------------- |
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd)        | `.venv\Scripts\activate.bat` |
| macOS / Linux        | `source .venv/bin/activate`  |

Pour le désactiver : `deactivate`.

> VS Code est déjà configuré (`.vscode/settings.json` à la racine) pour utiliser `backend/.venv`. Sinon : `Ctrl+Shift+P` → _Python: Select Interpreter_.

---

## 3. Lancer le serveur

**Mode développement** (rechargement automatique à chaque modification) :

```bash
uv run fastapi dev app/main.py
```

**Mode production** :

```bash
uv run fastapi run app/main.py
```

Changer le port / l'hôte :

```bash
uv run fastapi dev app/main.py --port 8080 --host 0.0.0.0
```

Une fois lancé :

- API : http://127.0.0.1:8000/api
- Documentation interactive (Swagger) : http://127.0.0.1:8000/api/docs
- Documentation ReDoc : http://127.0.0.1:8000/api/redoc

L'API est servie sous `/api` (`app.main:app` la monte ; [guide du déploiement](../docs/technical/deployment.md)). Le frontend l'appelle via le proxy Vite : une requête vers `http://localhost:5173/api/auth/me` est transmise telle quelle à `http://127.0.0.1:8000/api/auth/me`. Le backend doit donc tourner sur le port **8000** pendant le développement du frontend.

---

## 4. Gérer les packages

> ⚠️ N'utilisez pas `pip install` directement : passez toujours par `uv` pour que `pyproject.toml` et `uv.lock` restent à jour.

| Action                                       | Commande                                             |
| -------------------------------------------- | ---------------------------------------------------- |
| Ajouter un package                           | `uv add <package>` (ex : `uv add sqlalchemy`)        |
| Ajouter une version précise                  | `uv add "sqlalchemy>=2.0"`                           |
| Ajouter un package de dev (tests, lint…)     | `uv add --dev <package>` (ex : `uv add --dev ruff`)  |
| Supprimer un package                         | `uv remove <package>`                                |
| Mettre à jour un package                     | `uv lock --upgrade-package <package>` puis `uv sync` |
| Mettre à jour tous les packages              | `uv lock --upgrade` puis `uv sync`                   |
| Voir l'arbre des dépendances                 | `uv tree`                                            |
| Lister les packages installés                | `uv pip list`                                        |
| Réinstaller depuis le lockfile               | `uv sync`                                            |
| Installer sans les dépendances de dev (prod) | `uv sync --no-dev`                                   |

Exécuter n'importe quelle commande dans l'environnement du projet :

```bash
uv run python script.py
uv run <commande>
```

---

## 5. Tests

```bash
uv run pytest
```

Mode verbeux : `uv run pytest -v` — avec la couverture : `uv run pytest --cov=app`

Fonctionnement des tests (fixtures, tests d'intégration, écrire un nouveau test) : [guide des tests](../docs/technical/testing.md).

### Tests d'intégration (vrai PostgreSQL)

Les tests de `tests/integration/` (marqueur `integration`) tournent sur un vrai PostgreSQL :

- Lancez d'abord la base : `docker compose up -d --wait` (depuis la racine du dépôt).
- Ils utilisent une base dédiée `<POSTGRES_DB>_test` (ex. `tierlist_test`), créée automatiquement, avec les migrations Alembic appliquées : **les données de développement ne sont jamais touchées**.
- Chaque test s'exécute dans une transaction annulée à la fin.
- Si PostgreSQL est injoignable, ils sont **ignorés** en local, mais ils **échouent** en CI.

| Action                        | Commande                             |
| ----------------------------- | ------------------------------------ |
| Tests unitaires seulement     | `uv run pytest -m "not integration"` |
| Tests d'intégration seulement | `uv run pytest -m integration`       |

---

## 6. Lint et formatage (Ruff)

[Ruff](https://docs.astral.sh/ruff/) sert à la fois de linter et de formateur. Il est configuré dans `pyproject.toml` (section `[tool.ruff]`).

| Action                                   | Commande                       |
| ---------------------------------------- | ------------------------------ |
| Analyser le code                         | `uv run ruff check .`          |
| Corriger automatiquement                 | `uv run ruff check . --fix`    |
| Formater le code                         | `uv run ruff format .`         |
| Vérifier le formatage sans modifier (CI) | `uv run ruff format . --check` |

Le hook git `pre-commit` (voir le [README racine](../README.fr.md)) lance automatiquement `ruff check` et `ruff format --check` avant chaque commit. Pour corriger avant de commiter :

```bash
uv run ruff check . --fix && uv run ruff format .
```

> Dans VS Code, installez l'extension **Ruff** (`charliermarsh.ruff`) pour avoir le lint et le formatage à l'enregistrement.

### Vérification des types (Pyright)

```bash
uv run pyright
```

Configuré dans `pyproject.toml` (`[tool.pyright]`, mode `standard`, sur `app/`, `tests/` et `migrations/`). Lancé aussi par la CI.

---

## 7. Structure du projet

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # Point d'entrée FastAPI : API sous /api (santé, routers), build du frontend, lifespan
│   ├── api/
│   │   ├── dependencies.py # Dépendances communes (get_auth_service, get_current_user)
│   │   └── routes/auth.py # Routes /auth : register, login, refresh, logout, me
│   ├── constants/         # Valeurs fixes : auth.py, google.py, error_codes.py (ErrorCode), messages.py (textes de l'API), logging.py
│   ├── exceptions/        # Exceptions du domaine : auth.py, google.py ; http.py (AppHTTPException)
│   ├── core/
│   │   ├── config.py      # Configuration lue depuis .env (pydantic-settings)
│   │   ├── errors.py      # Format d'erreur unique (ErrorResponse, HTTPException, handlers 422 et 500)
│   │   ├── logging.py     # Logs de l'application (LOG_LEVEL, format uvicorn)
│   │   ├── monitoring.py  # Suivi des erreurs avec Sentry (SENTRY_DSN)
│   │   └── security.py    # Hachage des mots de passe (Argon2id), access tokens JWT, refresh tokens
│   ├── models/            # Modèles SQLAlchemy, un par fichier : user.py, refresh_token.py, oauth_account.py…
│   ├── repositories/      # Requêtes en base (users, refresh_tokens, oauth_accounts)
│   ├── schemas/auth.py    # Modèles Pydantic de requête / réponse de /auth
│   ├── services/          # Règles métier (auth.py : AuthService) et client Google (google_oauth.py)
│   └── db/
│       ├── base.py        # Classe Base des modèles SQLAlchemy
│       └── session.py     # Engine, session (dépendance FastAPI), ping de la base
├── migrations/            # Migrations Alembic (env.py, versions/)
├── scripts/
│   ├── export_openapi.py  # Écrit le contrat d'API dans openapi.json
│   ├── set_super_admin.py # Donne ou retire le rôle super admin (développement local)
│   └── seed.py            # Remplit la base locale ou de staging avec des données de test (docs/technical/seed-data.md)
├── tests/
│   ├── test_main.py       # Tests unitaires avec TestClient (sans base réelle)
│   ├── test_errors.py     # Tests du format d'erreur (500, 422, HTTPException, codes d'erreur)
│   ├── test_security.py   # Primitives mots de passe, JWT et refresh tokens
│   ├── test_google_oauth.py # Client Google (PKCE, vérification de l'id_token), sans réseau
│   └── integration/       # Tests sur un vrai PostgreSQL (base <POSTGRES_DB>_test)
├── .env.example           # Modèle de .env (identifiants PostgreSQL)
├── alembic.ini            # Configuration Alembic
├── .python-version        # Version de Python utilisée par uv
├── pyproject.toml         # Métadonnées + dépendances du projet
├── openapi.json           # Contrat d'API (généré, commité)
├── uv.lock                # Versions exactes verrouillées (à commiter)
└── README.md / README.fr.md   # Ce fichier (anglais / français)
```

---

## 8. Bonnes pratiques

- **Commitez** `pyproject.toml`, `uv.lock` et `.python-version`.
- **Ne commitez pas** `.venv/` (déjà dans `.gitignore`).
- Après un `git pull`, lancez `uv sync` pour vous remettre à jour.
- Changer de version de Python : `uv python pin 3.12` puis `uv sync`.
- **Ne commitez pas** `.env` : seul `.env.example` est versionné.

---

## 9. Base de données (PostgreSQL + SQLAlchemy + Alembic)

La base tourne dans Docker (`compose.yaml` à la racine du dépôt, voir le [README racine](../README.fr.md)). Le backend s'y connecte avec **SQLAlchemy 2** et le driver **psycopg 3**.

### Configuration

Copiez `.env.example` en `.env` (dans `backend/`) et adaptez les valeurs :

| Variable                                | Rôle                                                                                                                                                                                       | Défaut                                           |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------ |
| `POSTGRES_USER`                         | Utilisateur                                                                                                                                                                                | — (obligatoire)                                  |
| `POSTGRES_PASSWORD`                     | Mot de passe                                                                                                                                                                               | — (obligatoire)                                  |
| `POSTGRES_DB`                           | Nom de la base                                                                                                                                                                             | — (obligatoire)                                  |
| `POSTGRES_HOST`                         | Hôte vu depuis le backend                                                                                                                                                                  | `127.0.0.1`                                      |
| `POSTGRES_PORT`                         | Port                                                                                                                                                                                       | `5432`                                           |
| `DATABASE_CONNECT_TIMEOUT_SECONDS`      | Délai maximal pour se connecter à la base, en secondes                                                                                                                                     | `3`                                              |
| `LOG_LEVEL`                             | Niveau des logs de l'application : `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL` (insensible à la casse)                                                                               | `INFO`                                           |
| `JWT_SECRET_KEY`                        | Clé de signature des access tokens, 32 caractères minimum, différente dans chaque environnement. En générer une avec `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"` | — (obligatoire)                                  |
| `ACCESS_TOKEN_TTL_MINUTES`              | Durée de vie de l'access token, en minutes                                                                                                                                                 | `15`                                             |
| `REFRESH_TOKEN_TTL_DAYS`                | Durée de vie du refresh token, en jours                                                                                                                                                    | `30`                                             |
| `PASSWORD_MIN_LENGTH`                   | Longueur minimale du mot de passe à l'inscription (au plus 128) ; la 422 l'indique                                                                                                         | `8`                                              |
| `RECENT_AUTHENTICATION_MAX_AGE_MINUTES` | Compte créé avec Google : âge maximal de la connexion pour supprimer le compte                                                                                                             | `5`                                              |
| `EMAIL_VERIFICATION_TTL_HOURS`          | Validité du lien de confirmation de l'email, en heures                                                                                                                                     | `24`                                             |
| `PASSWORD_RESET_TTL_MINUTES`            | Validité du lien de réinitialisation du mot de passe, en minutes                                                                                                                           | `30`                                             |
| `EMAIL_COOLDOWN_SECONDS`                | Délai minimal entre deux emails du même type pour un compte (évite d'inonder une boîte)                                                                                                    | `60`                                             |
| `AUTH_COOKIE_SECURE`                    | Cookie de refresh envoyé en HTTPS uniquement ; `false` en local (HTTP)                                                                                                                     | `true`                                           |
| `AUTH_COOKIE_PATH`                      | Chemin du cookie de refresh : les routes d'authentification, sous `/api`                                                                                                                   | `/api/auth`                                      |
| `DELETED_TEMPLATE_RETENTION_DAYS`       | Jours pendant lesquels un template supprimé reste en base avant d'être purgé définitivement                                                                                                | `30`                                             |
| `MODERATION_LOG_RETENTION_DAYS`         | Jours pendant lesquels une entrée du journal de modération est gardée (3 ans, annoncés par la politique de confidentialité)                                                                | `1095`                                           |
| `ROOM_DEFAULT_TIMER_SECONDS`            | Timer par item d'une nouvelle salle, en secondes (5 à 300)                                                                                                                                 | `30`                                             |
| `ROOM_DEFAULT_COOLDOWN_SECONDS`         | Cooldown final d'une nouvelle salle, en secondes (10 à 600)                                                                                                                                | `60`                                             |
| `GUEST_LINK_TTL_DAYS`                   | Validité du lien perso d'un invité, en jours (30 au plus)                                                                                                                                  | `30`                                             |
| `ROOM_COOKIE_PATH`                      | Chemin des routes des salles (sous `/api`), base du cookie des invités                                                                                                                     | `/api/rooms`                                     |
| `ROOM_HEARTBEAT_INTERVAL_SECONDS`       | Canal temps réel : ping après ce silence du client, en secondes                                                                                                                            | `10`                                             |
| `ROOM_HEARTBEAT_TIMEOUT_SECONDS`        | Canal temps réel : socket fermé sans pong dans ce délai, en secondes                                                                                                                       | `5`                                              |
| `ROOM_PRESENCE_GRACE_SECONDS`           | Un participant devient déconnecté ce délai après la fermeture de son dernier socket, en secondes                                                                                           | `3`                                              |
| `ROOM_AUTH_TIMEOUT_SECONDS`             | Canal temps réel : délai du message d'authentification, en secondes                                                                                                                        | `5`                                              |
| `IMAGE_UPLOAD_MAX_BYTES`                | Taille maximale d'une image de tuile envoyée, en octets ; Cloudflare accepte des corps jusqu'à 100 Mo                                                                                      | `10485760` (10 Mio)                              |
| `IMAGE_MAX_SOURCE_PIXELS`               | Nombre maximal de pixels de l'image décodée (protection contre les bombes de décompression)                                                                                                | `40000000`                                       |
| `GOOGLE_CLIENT_ID`                      | ID client OAuth de la Google Cloud Console (Application Web) ; sans lui, la connexion Google est désactivée                                                                                | — (facultatif)                                   |
| `GOOGLE_CLIENT_SECRET`                  | Secret de ce client                                                                                                                                                                        | — (facultatif)                                   |
| `GOOGLE_REDIRECT_URI`                   | URL de retour, identique à un URI de redirection autorisé du client                                                                                                                        | `http://localhost:5173/api/auth/google/callback` |
| `GOOGLE_LOGIN_ATTEMPT_TTL_MINUTES`      | Temps laissé sur la page de Google avant que la tentative expire                                                                                                                           | `10`                                             |
| `GOOGLE_HTTP_TIMEOUT_SECONDS`           | Délai des appels vers Google (échange du code, clés publiques)                                                                                                                             | `10`                                             |
| `FRONTEND_DIST`                         | Build Vite servi par FastAPI ; absent en développement (Vite sert le frontend)                                                                                                             | `frontend_dist/` à côté de `backend/`            |
| `APP_RELEASE`                           | Version qui tourne, renvoyée par `/api/health` ; écrite par le déploiement                                                                                                                 | `dev`                                            |
| `MAINTENANCE_ENABLED`                   | Purges de nuit (templates supprimés, images inutilisées) dans le processus                                                                                                                 | `true`                                           |
| `MAINTENANCE_HOUR_UTC`                  | Heure des purges de nuit, en UTC (0 à 23)                                                                                                                                                  | `3`                                              |

Les emails (`SMTP_*`, `EMAIL_FROM`, `FRONTEND_BASE_URL`, tous facultatifs) sont décrits dans le [guide des emails](../docs/technical/emails.md). L'authentification est décrite dans le [guide de l'authentification](../docs/technical/authentication.md), les templates et leur purge dans le [guide des templates](../docs/technical/templates.md), les salles, leurs durées par défaut (`ROOM_DEFAULT_*`) et les invités (`GUEST_LINK_TTL_DAYS`, `ROOM_COOKIE_PATH`) dans le [guide des salles](../docs/technical/rooms.md), le canal temps réel (`ROOM_HEARTBEAT_*`, `ROOM_PRESENCE_GRACE_SECONDS`, `ROOM_AUTH_TIMEOUT_SECONDS`) dans le [guide du temps réel](../docs/technical/realtime.md#3-in-the-code), les images des tuiles, leur stockage S3 (`IMAGE_S3_*`, `IMAGE_PUBLIC_BASE_URL` ; valeurs de SeaweedFS dans `.env.example`), la limite d'envois (`IMAGE_UPLOADS_PER_HOUR_MAX`) et le ramasse-miettes (`UNUSED_IMAGE_RETENTION_DAYS`) dans le [guide des images](../docs/technical/images.md#24-limits-and-settings). Comme le conteneur PostgreSQL lit aussi `.env`, les variables d'authentification lui sont transmises : sans conséquence, il les ignore.

Ce même fichier est lu par le conteneur PostgreSQL : changer le mot de passe **après** la création du volume n'a pas d'effet sur une base existante (il faut alors `docker compose down -v`, qui efface les données).

### Sondes de santé

`GET /api/health` indique seulement que l'application tourne (`200 {"status": "ok", "release": "<APP_RELEASE>"}`), sans toucher à la base : c'est la sonde de vie à donner à l'hébergeur, pour qu'une panne de la base ne leur fasse pas redémarrer une application qui fonctionne.

`GET /api/health/db` exécute `SELECT 1` : `200 {"status": "ok", "release": …}` si la base répond, sinon `503 {"detail": "Database unavailable", "code": "database_unavailable"}` (l'erreur détaillée est dans les logs du backend).

### Migrations (Alembic)

| Action                                   | Commande                                                  |
| ---------------------------------------- | --------------------------------------------------------- |
| Créer une migration à partir des modèles | `uv run alembic revision --autogenerate -m "description"` |
| Appliquer les migrations                 | `uv run alembic upgrade head`                             |
| Annuler la dernière migration            | `uv run alembic downgrade -1`                             |
| Voir la version actuelle de la base      | `uv run alembic current`                                  |

Les modèles doivent hériter de `app.db.base.Base` et être importés par `migrations/env.py` pour être détectés par `--autogenerate`. **Relisez toujours** une migration générée avant de l'appliquer.

Les noms des contraintes et des index suivent la convention de `app/db/base.py` (`pk_users`, `uq_users_email`, `fk_refresh_tokens_user_id_users`, `ix_refresh_tokens_user_id`…) : une migration peut les désigner par leur nom sans deviner celui choisi par PostgreSQL.

`tests/integration/test_migrations.py` échoue quand les modèles et les migrations ne décrivent plus le même schéma, ou quand une migration ne peut pas être annulée.

### Rôle super admin en local

Les super admins modèrent l'application ([guide de l'authentification](../docs/technical/authentication.md#super-admins)). Le rôle n'est jamais donné par l'API : en développement local, donnez-le à un compte existant avec

```bash
uv run python scripts/set_super_admin.py alice@example.com            # donne le rôle
uv run python scripts/set_super_admin.py alice@example.com --revoke   # le retire
```

L'e-mail ignore la casse ; un e-mail inconnu sort avec le code `1`. Rechargez la page pour voir le lien « Modération ». En staging et en production, utilisez la requête SQL du [guide du déploiement](../docs/technical/deployment.md#512-super-admins).

---

## 10. Logs

Les logs de l'application (loggers sous `app`, par ex. `logging.getLogger(__name__)` dans `app/...`) sont configurés par `app/core/logging.py` :

- écrits sur stderr au **même format qu'uvicorn**, avec en plus le nom du logger : `ERROR:    app.main - Échec de la connexion à la base de données` ;
- niveau réglé par `LOG_LEVEL` (dans `.env` ou l'environnement, `INFO` par défaut) ; une valeur invalide arrête l'application au démarrage avec une erreur claire ;
- les logs d'uvicorn gardent leur propre configuration : utilisez `--log-level` sur `fastapi dev` / `fastapi run` pour les régler ;
- les logs `ERROR` partent aussi vers Sentry quand `SENTRY_DSN` est défini (`SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE` ; `app/core/monitoring.py`) : voir le [guide du suivi des erreurs](../docs/technical/monitoring.md).

---

## 11. Contrat d'API (OpenAPI)

`openapi.json` est un instantané du contrat d'API : le schéma OpenAPI que FastAPI construit à partir des routes et des modèles Pydantic (celui qui alimente `/docs`). Il est commité : chaque PR montre si elle modifie l'API, et le frontend en **génère ses types TypeScript** (`pnpm gen:api`) au lieu de les recopier à la main.

Quand vous ajoutez ou modifiez une route ou un schéma Pydantic :

1. `uv run python scripts/export_openapi.py` (dans `backend/`) met à jour `openapi.json` ;
2. `pnpm gen:api` (dans `frontend/`) régénère les types TypeScript ;
3. corrigez les éventuelles erreurs de `pnpm typecheck` : elles montrent le code frontend touché par le changement ;
4. commitez ensemble `backend/openapi.json` et `frontend/src/api/schema.d.ts`.

Si vous oubliez l'étape 1, le test backend `test_openapi_schema_is_up_to_date` échoue ; si vous oubliez l'étape 2, l'étape CI « Check API types are up to date » échoue.

---

## 12. Format d'erreur

Toute réponse d'erreur de l'API a la même forme JSON, `ErrorResponse` (`app/core/errors.py`), exposée dans le contrat OpenAPI :

```json
{
  "detail": "Invalid request",
  "code": "validation_error",
  "errors": [
    {
      "field": "body.password",
      "message": "…",
      "code": "password_too_short",
      "params": { "min_length": 8 }
    }
  ]
}
```

- `code` : code d'erreur stable, lisible par une machine. **Le frontend traduit l'erreur à partir de `code` et `params`** : il n'affiche pas `detail`.
- `params` (facultatif) : valeurs utilisées par la traduction (ex. `min_length`).
- `detail` : texte anglais, réservé aux développeurs et aux logs.

| Cas                                                               | Statut      | Corps                                                                                                                                                                                                                                |
| ----------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `AppHTTPException` levée par une route (`app/exceptions/http.py`) | celui donné | `detail` + son `code` (un `ErrorCode`) + `params` facultatifs ; en-têtes conservés (`WWW-Authenticate`, `set-cookie`)                                                                                                                |
| Autre `HTTPException` (ex. 404/405 de FastAPI)                    | celui donné | `detail` + `code: "http_error"`                                                                                                                                                                                                      |
| Requête invalide (chemin, query, corps)                           | `422`       | `code: "validation_error"` + `errors` : une entrée par champ invalide (`field` = emplacement, `message`, `code` = type d'erreur Pydantic comme `missing` ou `string_too_short`, `params` = son contexte scalaire comme `min_length`) |
| Exception non prévue                                              | `500`       | `{"detail": "Internal server error", "code": "internal_error"}` : aucun détail interne n'est envoyé au client ; l'erreur est journalisée avec sa trace, la méthode et le chemin                                                      |

Codes d'erreur (`ErrorCode`, `app/constants/error_codes.py`) :

| Code                           | Statut          | Signification                                                                                                                                        |
| ------------------------------ | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `internal_error`               | 500             | Erreur imprévue                                                                                                                                      |
| `validation_error`             | 422             | Requête invalide (voir `errors`)                                                                                                                     |
| `http_error`                   | tous            | `HTTPException` sans code dédié                                                                                                                      |
| `database_unavailable`         | 503             | `GET /health/db` : la base ne répond pas                                                                                                             |
| `not_authenticated`            | 401 / WS `4401` | Access token absent ou invalide (canal temps réel : pas d'`auth` à temps, ou compte banni)                                                           |
| `email_already_registered`     | 409             | Inscription avec un email déjà utilisé                                                                                                               |
| `invalid_credentials`          | 401             | Email ou mot de passe incorrect                                                                                                                      |
| `session_expired`              | 401             | Refresh token expiré ou révoqué (aucun cookie : `204`)                                                                                               |
| `incorrect_password`           | 403             | Mot de passe faux à la suppression du compte                                                                                                         |
| `reauthentication_required`    | 403             | Compte Google dont la dernière connexion est trop ancienne pour confirmer la suppression                                                             |
| `invalid_token`                | 400             | Lien reçu par email invalide, expiré ou qui ne correspond plus au compte                                                                             |
| `password_too_short`           | 422 (champ)     | Mot de passe plus court que `PASSWORD_MIN_LENGTH` ; `params.min_length`                                                                              |
| `email_not_verified`           | 403             | Modèle rendu public par un compte dont l'email n'est pas confirmé                                                                                    |
| `template_not_found`           | 404 / 409       | Modèle inconnu, supprimé ou appartenant à un autre utilisateur (indiscernables) ; `409` quand une partie démarre avec un modèle supprimé entre-temps |
| `image_unsupported_format`     | 415             | `POST /images` : pas une image JPEG, PNG ou WebP, ou illisible                                                                                       |
| `image_too_large`              | 413             | `POST /images` : fichier au-delà de `IMAGE_UPLOAD_MAX_BYTES` ; `params.max_bytes`                                                                    |
| `image_too_many_pixels`        | 422             | `POST /images` : image décodée au-delà de `IMAGE_MAX_SOURCE_PIXELS`                                                                                  |
| `image_upload_limit_reached`   | 429             | `POST /images` : `IMAGE_UPLOADS_PER_HOUR_MAX` atteint ; `params.max_uploads`                                                                         |
| `image_not_found`              | 404             | `image_id` d'une tuile inconnue ou d'un autre utilisateur                                                                                            |
| `tile_empty`                   | 422             | Tuile sans texte ni image                                                                                                                            |
| `super_admin_required`         | 403             | Route réservée à un super admin                                                                                                                      |
| `account_not_found`            | 404             | Modération : compte inconnu                                                                                                                          |
| `account_banned`               | 403             | Connexion d'un compte banni définitivement ; `params.reason`                                                                                         |
| `account_banned_until`         | 403             | Connexion d'un compte banni jusqu'à une date ; `params.reason`, `params.ends_at`                                                                     |
| `cannot_ban_super_admin`       | 409             | Un super admin ne peut pas être banni                                                                                                                |
| `account_not_banned`           | 409             | Lever le bannissement d'un compte qui n'en a pas                                                                                                     |
| `ban_end_in_past`              | 422             | Fin d'un bannissement qui n'est pas dans le futur                                                                                                    |
| `template_has_no_tiles`        | 409             | Salle créée, partie lancée ou modèle rendu public, avec un modèle sans tuile                                                                         |
| `template_hidden`              | 409             | Salle créée, partie lancée ou modèle rendu public, avec un modèle masqué par la modération                                                           |
| `template_moderation_conflict` | 409             | Action de modération qui ne correspond pas à l'état du modèle                                                                                        |
| `tier_not_found`               | 404             | Tier inconnu du modèle (ou de la partie au placement)                                                                                                |
| `last_tier`                    | 409             | Supprimer le dernier tier d'un modèle                                                                                                                |
| `tile_not_found`               | 404             | Tuile inconnue du modèle                                                                                                                             |
| `tile_limit_reached`           | 409             | Modèle déjà à sa limite de tuiles ; `params.max_tiles`                                                                                               |
| `room_not_found`               | 404 / WS `4404` | Code de salle inconnu ou salle fermée                                                                                                                |
| `room_not_joined`              | 403             | Lire une salle sans y avoir de place                                                                                                                 |
| `room_admin_required`          | 403             | Action réservée au room admin                                                                                                                        |
| `room_settings_locked`         | 409             | Réglage modifié pendant une partie (seules les arrivées tardives le peuvent)                                                                         |
| `room_full`                    | 409             | Salle déjà pleine ; `params.max_participants`                                                                                                        |
| `room_locked`                  | 409             | Rejoindre pendant une partie dont la salle est verrouillée                                                                                           |
| `nickname_taken`               | 409             | Pseudo d'invité déjà utilisé dans la salle                                                                                                           |
| `guest_link_invalid`           | 404             | Lien personnel d'invité expiré, ou sa salle fermée                                                                                                   |
| `participant_not_found`        | 404             | Participant inconnu de la salle                                                                                                                      |
| `cannot_remove_room_admin`     | 409             | Retirer le room admin de sa salle                                                                                                                    |
| `room_banned`                  | 403 / WS `4411` | Compte ou navigateur banni de la salle                                                                                                               |
| `ban_not_found`                | 404             | Bannissement inconnu de la salle                                                                                                                     |
| `invalid_message`              | WS `4400`       | Canal temps réel : message inattendu                                                                                                                 |
| `heartbeat_timeout`            | WS `4408`       | Canal temps réel : pas de réponse au heartbeat                                                                                                       |
| `removed_from_room`            | WS `4410`       | Canal temps réel : retiré par le room admin (ou compte supprimé)                                                                                     |
| `room_closed`                  | WS `4412`       | Canal temps réel : la salle a été fermée                                                                                                             |
| `game_in_progress`             | 409             | Lancer une partie alors qu'une autre est en cours                                                                                                    |
| `no_placing_participant`       | 409             | Lancer une partie où personne ne place les éléments                                                                                                  |
| `round_not_in_progress`        | 409             | Placer, ou passer à la suite, sans tour en cours                                                                                                     |
| `not_a_placing_participant`    | 403             | Le room admin qui ne joue pas place un élément                                                                                                       |
| `item_not_current`             | 409             | Placer un élément qui n'est pas celui du tour en cours                                                                                               |
| `item_not_in_game`             | 404             | Placer, pendant les retouches finales, un élément hors de la partie                                                                                  |
| `cooldown_not_in_progress`     | 409             | Terminer les retouches finales quand elles ne sont pas en cours                                                                                      |
| `cooldown_over`                | 409             | Placer après la fin des retouches finales                                                                                                            |
| `results_not_found`            | 404             | Lien de résultats inconnu (ou partie masquée par la modération)                                                                                      |
| `image_moderation_conflict`    | 409             | Action de modération qui ne correspond pas à l'état de l'image                                                                                       |
| `report_target_not_found`      | 404             | Signaler un contenu inconnu ou déjà retiré                                                                                                           |
| `report_already_open`          | 409             | Contenu déjà signalé par la même personne                                                                                                            |
| `report_details_required`      | 422             | Motif `other` sans précisions                                                                                                                        |
| `report_limit_reached`         | 429             | Limite de signalements par heure atteinte ; `params.max_reports`                                                                                     |
| `reports_not_open`             | 404             | Classer un contenu sans signalement ouvert                                                                                                           |
| `nickname_not_found`           | 404             | Retirer le pseudo d'aucun compte ni invité                                                                                                           |
| `game_not_found`               | 404             | Modération : partie close inconnue                                                                                                                   |
| `game_moderation_conflict`     | 409             | Action de modération qui ne correspond pas à l'état de la partie                                                                                     |
| `images_hiding_in_progress`    | 409             | `POST /moderation/accounts/{id}/hide-images` pendant qu'un lot du même compte tourne                                                                 |

Pour les erreurs prévues (introuvable, conflit…), levez une `AppHTTPException` avec un `ErrorCode` et un `detail` en anglais (`app/constants/messages.py`), et laissez les erreurs imprévues remonter jusqu'au handler générique : n'attrapez jamais `Exception` dans une route juste pour renvoyer une 500. **Tout nouveau code d'erreur doit être traduit dans chaque langue du frontend.** Côté frontend, `ApiError` expose `status`, `body`, et le `detail` comme `message`.
