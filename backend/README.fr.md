# TierList — Backend FastAPI

[English](README.md) | Français

Backend Python basé sur [FastAPI](https://fastapi.tiangolo.com/), géré avec le gestionnaire de paquets et de projets [uv](https://docs.astral.sh/uv/).

> Ce dossier fait partie du dépôt [TierList](../README.fr.md). **Toutes les commandes ci-dessous se lancent depuis le dossier `backend/`** (`cd backend`).

---

## 1. Prérequis

- **uv** (il installe et gère lui-même Python si besoin)
- Python **3.11+** (version fixée dans `.python-version`)

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

- API : http://127.0.0.1:8000
- Documentation interactive (Swagger) : http://127.0.0.1:8000/docs
- Documentation ReDoc : http://127.0.0.1:8000/redoc

Le frontend appelle le backend via le proxy Vite : une requête vers `http://localhost:5173/api/hello` est redirigée vers `http://127.0.0.1:8000/hello`. Le backend doit donc tourner sur le port **8000** pendant le développement du frontend.

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

Ce que fait chaque test, son but et le résultat attendu : [guide des tests](../docs/testing.fr.md).

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
│   ├── main.py            # Point d'entrée FastAPI (GET /hello, GET /health, GET /health/db, routers)
│   ├── api/
│   │   ├── dependencies.py # Dépendances communes (get_auth_service, get_current_user)
│   │   └── routes/auth.py # Routes /auth : register, login, refresh, logout, me
│   ├── constants/         # Valeurs fixes : auth.py, google.py, error_codes.py (ErrorCode), messages.py (textes de l'API), logging.py
│   ├── exceptions/        # Exceptions du domaine : auth.py, google.py ; http.py (AppHTTPException)
│   ├── core/
│   │   ├── config.py      # Configuration lue depuis .env (pydantic-settings)
│   │   ├── errors.py      # Format d'erreur unique (ErrorResponse, HTTPException, handlers 422 et 500)
│   │   ├── logging.py     # Logs de l'application (LOG_LEVEL, format uvicorn)
│   │   └── security.py    # Hachage des mots de passe (Argon2id), access tokens JWT, refresh tokens
│   ├── models/user.py     # User, RefreshToken et OAuthAccount (SQLAlchemy)
│   ├── repositories/      # Requêtes en base (users, refresh_tokens, oauth_accounts)
│   ├── schemas/auth.py    # Modèles Pydantic de requête / réponse de /auth
│   ├── services/          # Règles métier (auth.py : AuthService) et client Google (google_oauth.py)
│   └── db/
│       ├── base.py        # Classe Base des modèles SQLAlchemy
│       └── session.py     # Engine, session (dépendance FastAPI), ping de la base
├── migrations/            # Migrations Alembic (env.py, versions/)
├── scripts/
│   └── export_openapi.py  # Écrit le contrat d'API dans openapi.json
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
| `AUTH_COOKIE_SECURE`                    | Cookie de refresh envoyé en HTTPS uniquement ; `false` en local (HTTP)                                                                                                                     | `true`                                           |
| `AUTH_COOKIE_PATH`                      | Chemin du cookie de refresh, vu par le navigateur (à travers le proxy `/api`)                                                                                                              | `/api/auth`                                      |
| `GOOGLE_CLIENT_ID`                      | ID client OAuth de la Google Cloud Console (Application Web) ; sans lui, la connexion Google est désactivée                                                                                | — (facultatif)                                   |
| `GOOGLE_CLIENT_SECRET`                  | Secret de ce client                                                                                                                                                                        | — (facultatif)                                   |
| `GOOGLE_REDIRECT_URI`                   | URL de retour, identique à un URI de redirection autorisé du client                                                                                                                        | `http://localhost:5173/api/auth/google/callback` |
| `GOOGLE_LOGIN_ATTEMPT_TTL_MINUTES`      | Temps laissé sur la page de Google avant que la tentative expire                                                                                                                           | `10`                                             |
| `GOOGLE_HTTP_TIMEOUT_SECONDS`           | Délai des appels vers Google (échange du code, clés publiques)                                                                                                                             | `10`                                             |

L'authentification est décrite dans le [guide de l'authentification](../docs/authentication.fr.md). Comme le conteneur PostgreSQL lit aussi `.env`, les variables d'authentification lui sont transmises : sans conséquence, il les ignore.

Ce même fichier est lu par le conteneur PostgreSQL : changer le mot de passe **après** la création du volume n'a pas d'effet sur une base existante (il faut alors `docker compose down -v`, qui efface les données).

### Sondes de santé

`GET /health` indique seulement que l'application tourne (`200 {"status": "ok"}`), sans toucher à la base : c'est la sonde de vie à donner à Docker ou à un hébergeur, pour qu'une panne de la base ne leur fasse pas redémarrer une application qui fonctionne.

`GET /health/db` exécute `SELECT 1` : `200 {"status": "ok"}` si la base répond, sinon `503 {"detail": "Database unavailable", "code": "database_unavailable"}` (l'erreur détaillée est dans les logs du backend).

### Migrations (Alembic)

| Action                                   | Commande                                                  |
| ---------------------------------------- | --------------------------------------------------------- |
| Créer une migration à partir des modèles | `uv run alembic revision --autogenerate -m "description"` |
| Appliquer les migrations                 | `uv run alembic upgrade head`                             |
| Annuler la dernière migration            | `uv run alembic downgrade -1`                             |
| Voir la version actuelle de la base      | `uv run alembic current`                                  |

Les modèles doivent hériter de `app.db.base.Base` et être importés par `migrations/env.py` pour être détectés par `--autogenerate`. **Relisez toujours** une migration générée avant de l'appliquer.

---

## 10. Logs

Les logs de l'application (loggers sous `app`, par ex. `logging.getLogger(__name__)` dans `app/...`) sont configurés par `app/core/logging.py` :

- écrits sur stderr au **même format qu'uvicorn**, avec en plus le nom du logger : `ERROR:    app.main - Échec de la connexion à la base de données` ;
- niveau réglé par `LOG_LEVEL` (dans `.env` ou l'environnement, `INFO` par défaut) ; une valeur invalide arrête l'application au démarrage avec une erreur claire ;
- les logs d'uvicorn gardent leur propre configuration : utilisez `--log-level` sur `fastapi dev` / `fastapi run` pour les régler.

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

| Code                        | Statut      | Signification                                                                            |
| --------------------------- | ----------- | ---------------------------------------------------------------------------------------- |
| `internal_error`            | 500         | Erreur imprévue                                                                          |
| `validation_error`          | 422         | Requête invalide (voir `errors`)                                                         |
| `http_error`                | tous        | `HTTPException` sans code dédié                                                          |
| `database_unavailable`      | 503         | `GET /health/db` : la base ne répond pas                                                 |
| `not_authenticated`         | 401         | Access token absent ou invalide                                                          |
| `email_already_registered`  | 409         | Inscription avec un email déjà utilisé                                                   |
| `invalid_credentials`       | 401         | Email ou mot de passe incorrect                                                          |
| `session_expired`           | 401         | Refresh token absent, expiré ou révoqué                                                  |
| `incorrect_password`        | 403         | Mot de passe faux à la suppression du compte                                             |
| `reauthentication_required` | 403         | Compte Google dont la dernière connexion est trop ancienne pour confirmer la suppression |
| `password_too_short`        | 422 (champ) | Mot de passe plus court que `PASSWORD_MIN_LENGTH` ; `params.min_length`                  |

Pour les erreurs prévues (introuvable, conflit…), levez une `AppHTTPException` avec un `ErrorCode` et un `detail` en anglais (`app/constants/messages.py`), et laissez les erreurs imprévues remonter jusqu'au handler générique : n'attrapez jamais `Exception` dans une route juste pour renvoyer une 500. **Tout nouveau code d'erreur doit être traduit dans chaque langue du frontend.** Côté frontend, `ApiError` expose `status`, `body`, et le `detail` comme `message`.
