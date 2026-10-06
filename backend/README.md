# TierList — FastAPI backend

English | [Français](README.fr.md)

Python backend built with [FastAPI](https://fastapi.tiangolo.com/), managed with the [uv](https://docs.astral.sh/uv/) package and project manager.

> This folder is part of the [TierList](../README.md) repository. **All commands below are run from the `backend/` folder** (`cd backend`).

---

## 1. Prerequisites

- **uv** (it installs and manages Python itself if needed)
- Python **3.11+** (version pinned in `.python-version`)

### Installing uv

**Windows (PowerShell)**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux**:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then restart your terminal and check:

```bash
uv --version
```

---

## 2. Installing the project

From the `backend/` folder:

```bash
uv sync
```

This command:

- creates the `.venv/` virtual environment if it does not exist;
- installs all dependencies (dev ones included) at the exact versions of `uv.lock`.

### Activating the virtual environment (optional)

With `uv run`, activation is **not needed**: uv uses `.venv` automatically.
If you still want to activate it (e.g. to call `python` or `fastapi` directly):

| System               | Command                      |
| -------------------- | ---------------------------- |
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd)        | `.venv\Scripts\activate.bat` |
| macOS / Linux        | `source .venv/bin/activate`  |

To deactivate it: `deactivate`.

> VS Code is already configured (`.vscode/settings.json` at the root) to use `backend/.venv`. Otherwise: `Ctrl+Shift+P` → _Python: Select Interpreter_.

---

## 3. Running the server

**Development mode** (auto-reload on every change):

```bash
uv run fastapi dev app/main.py
```

**Production mode**:

```bash
uv run fastapi run app/main.py
```

Change the port / host:

```bash
uv run fastapi dev app/main.py --port 8080 --host 0.0.0.0
```

Once running:

- API: http://127.0.0.1:8000
- Interactive documentation (Swagger): http://127.0.0.1:8000/docs
- ReDoc documentation: http://127.0.0.1:8000/redoc

The frontend calls the backend through the Vite proxy: a request to `http://localhost:5173/api/auth/me` is forwarded to `http://127.0.0.1:8000/auth/me`. The backend must therefore run on port **8000** during frontend development.

---

## 4. Managing packages

> ⚠️ Do not use `pip install` directly: always go through `uv` so that `pyproject.toml` and `uv.lock` stay up to date.

| Action                                  | Command                                              |
| --------------------------------------- | ---------------------------------------------------- |
| Add a package                           | `uv add <package>` (e.g. `uv add sqlalchemy`)        |
| Add a specific version                  | `uv add "sqlalchemy>=2.0"`                           |
| Add a dev package (tests, lint…)        | `uv add --dev <package>` (e.g. `uv add --dev ruff`)  |
| Remove a package                        | `uv remove <package>`                                |
| Upgrade a package                       | `uv lock --upgrade-package <package>` then `uv sync` |
| Upgrade all packages                    | `uv lock --upgrade` then `uv sync`                   |
| Show the dependency tree                | `uv tree`                                            |
| List installed packages                 | `uv pip list`                                        |
| Reinstall from the lockfile             | `uv sync`                                            |
| Install without dev dependencies (prod) | `uv sync --no-dev`                                   |

Run any command inside the project environment:

```bash
uv run python script.py
uv run <command>
```

---

## 5. Tests

```bash
uv run pytest
```

Verbose mode: `uv run pytest -v` — with coverage: `uv run pytest --cov=app`

What each test does, its purpose and expected result: [testing guide](../docs/technical/testing.md).

### Integration tests (real PostgreSQL)

Tests under `tests/integration/` (marker `integration`) run against a real PostgreSQL:

- Start the database first: `docker compose up -d --wait` (from the repository root).
- They use a dedicated `<POSTGRES_DB>_test` database (e.g. `tierlist_test`), created automatically, with the Alembic migrations applied: **development data is never touched**.
- Each test runs in a transaction that is rolled back at the end.
- If PostgreSQL is not reachable, they are **skipped** locally, but they **fail** on CI.

| Action                 | Command                              |
| ---------------------- | ------------------------------------ |
| Unit tests only        | `uv run pytest -m "not integration"` |
| Integration tests only | `uv run pytest -m integration`       |

---

## 6. Lint and formatting (Ruff)

[Ruff](https://docs.astral.sh/ruff/) is both the linter and the formatter. It is configured in `pyproject.toml` (`[tool.ruff]` section).

| Action                                       | Command                        |
| -------------------------------------------- | ------------------------------ |
| Analyze the code                             | `uv run ruff check .`          |
| Fix automatically                            | `uv run ruff check . --fix`    |
| Format the code                              | `uv run ruff format .`         |
| Check formatting without changing files (CI) | `uv run ruff format . --check` |

The `pre-commit` git hook (see the [root README](../README.md)) automatically runs `ruff check` and `ruff format --check` before each commit. To fix things before committing:

```bash
uv run ruff check . --fix && uv run ruff format .
```

> In VS Code, install the **Ruff** extension (`charliermarsh.ruff`) to get linting and formatting on save.

### Type checking (Pyright)

```bash
uv run pyright
```

Configured in `pyproject.toml` (`[tool.pyright]`, `standard` mode, on `app/`, `tests/` and `migrations/`). Also run by CI.

---

## 7. Project structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI entry point (GET /health, GET /health/db, routers)
│   ├── api/
│   │   ├── dependencies.py # Shared dependencies (get_auth_service, get_current_user)
│   │   └── routes/auth.py # /auth routes: register, login, refresh, logout, me
│   ├── constants/         # Fixed values: auth.py, google.py, error_codes.py (ErrorCode), messages.py (API texts), logging.py
│   ├── exceptions/        # Domain exceptions: auth.py, google.py; http.py (AppHTTPException)
│   ├── core/
│   │   ├── config.py      # Configuration read from .env (pydantic-settings)
│   │   ├── errors.py      # Single error format (ErrorResponse, HTTPException, 422 and 500 handlers)
│   │   ├── logging.py     # Application logging (LOG_LEVEL, uvicorn format)
│   │   └── security.py    # Password hashing (Argon2id), JWT access tokens, refresh tokens
│   ├── models/user.py     # User, RefreshToken and OAuthAccount (SQLAlchemy)
│   ├── repositories/      # Database queries (users, refresh_tokens, oauth_accounts)
│   ├── schemas/auth.py    # Pydantic request / response models of /auth
│   ├── services/          # Business rules (auth.py: AuthService) and Google client (google_oauth.py)
│   └── db/
│       ├── base.py        # Base class for SQLAlchemy models
│       └── session.py     # Engine, session (FastAPI dependency), database ping
├── migrations/            # Alembic migrations (env.py, versions/)
├── scripts/
│   └── export_openapi.py  # Writes the API contract to openapi.json
├── tests/
│   ├── test_main.py       # Unit tests with TestClient (no real database)
│   ├── test_errors.py     # Error format tests (500, 422, HTTPException, error codes)
│   ├── test_security.py   # Password, JWT and refresh token primitives
│   ├── test_google_oauth.py # Google client (PKCE, id_token check), without network
│   └── integration/       # Tests against a real PostgreSQL (database <POSTGRES_DB>_test)
├── .env.example           # .env template (PostgreSQL credentials)
├── alembic.ini            # Alembic configuration
├── .python-version        # Python version used by uv
├── pyproject.toml         # Project metadata + dependencies
├── openapi.json           # API contract (generated, committed)
├── uv.lock                # Exact locked versions (to commit)
└── README.md / README.fr.md   # This file (English / French)
```

---

## 8. Good practices

- **Commit** `pyproject.toml`, `uv.lock` and `.python-version`.
- **Do not commit** `.venv/` (already in `.gitignore`).
- After a `git pull`, run `uv sync` to get up to date.
- Change the Python version: `uv python pin 3.12` then `uv sync`.
- **Do not commit** `.env`: only `.env.example` is versioned.

---

## 9. Database (PostgreSQL + SQLAlchemy + Alembic)

The database runs in Docker (`compose.yaml` at the repository root, see the [root README](../README.md)). The backend connects to it with **SQLAlchemy 2** and the **psycopg 3** driver.

### Configuration

Copy `.env.example` to `.env` (in `backend/`) and adjust the values:

| Variable                                | Purpose                                                                                                                                                                      | Default                                          |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `POSTGRES_USER`                         | User                                                                                                                                                                         | — (required)                                     |
| `POSTGRES_PASSWORD`                     | Password                                                                                                                                                                     | — (required)                                     |
| `POSTGRES_DB`                           | Database name                                                                                                                                                                | — (required)                                     |
| `POSTGRES_HOST`                         | Host as seen from the backend                                                                                                                                                | `127.0.0.1`                                      |
| `POSTGRES_PORT`                         | Port                                                                                                                                                                         | `5432`                                           |
| `DATABASE_CONNECT_TIMEOUT_SECONDS`      | Maximum time to connect to the database, in seconds                                                                                                                          | `3`                                              |
| `LOG_LEVEL`                             | Application log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL` (case-insensitive)                                                                                  | `INFO`                                           |
| `JWT_SECRET_KEY`                        | Key signing the access tokens, 32 characters minimum, different in each environment. Generate one with `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"` | — (required)                                     |
| `ACCESS_TOKEN_TTL_MINUTES`              | Access token lifetime, in minutes                                                                                                                                            | `15`                                             |
| `REFRESH_TOKEN_TTL_DAYS`                | Refresh token lifetime, in days                                                                                                                                              | `30`                                             |
| `PASSWORD_MIN_LENGTH`                   | Minimum password length at registration (at most 128); the 422 states it                                                                                                     | `8`                                              |
| `RECENT_AUTHENTICATION_MAX_AGE_MINUTES` | Account created with Google: maximum age of the sign-in to delete the account                                                                                                | `5`                                              |
| `EMAIL_VERIFICATION_TTL_HOURS`          | Validity of the email confirmation link, in hours                                                                                                                            | `24`                                             |
| `PASSWORD_RESET_TTL_MINUTES`            | Validity of the password reset link, in minutes                                                                                                                              | `30`                                             |
| `EMAIL_COOLDOWN_SECONDS`                | Minimum time between two emails of the same type for one account (prevents flooding a mailbox)                                                                               | `60`                                             |
| `AUTH_COOKIE_SECURE`                    | Refresh cookie sent over HTTPS only; set `false` locally (HTTP)                                                                                                              | `true`                                           |
| `AUTH_COOKIE_PATH`                      | Refresh cookie path, as seen by the browser (through the `/api` proxy)                                                                                                       | `/api/auth`                                      |
| `GOOGLE_CLIENT_ID`                      | OAuth client ID of the Google Cloud Console (Web application); without it, Google sign-in is disabled                                                                        | — (optional)                                     |
| `GOOGLE_CLIENT_SECRET`                  | Secret of that client                                                                                                                                                        | — (optional)                                     |
| `GOOGLE_REDIRECT_URI`                   | Callback URL, identical to an authorized redirect URI of the client                                                                                                          | `http://localhost:5173/api/auth/google/callback` |
| `GOOGLE_LOGIN_ATTEMPT_TTL_MINUTES`      | Time allowed on Google's page before the sign-in attempt expires                                                                                                             | `10`                                             |
| `GOOGLE_HTTP_TIMEOUT_SECONDS`           | Timeout of the calls to Google (code exchange, public keys)                                                                                                                  | `10`                                             |

Emails (`SMTP_*`, `EMAIL_FROM`, `FRONTEND_BASE_URL`, all optional) are described in the [emails guide](../docs/technical/emails.md). Authentication is described in the [authentication guide](../docs/technical/authentication.md). Since the PostgreSQL container also reads `.env`, the authentication variables are passed to it too: harmless, as it ignores them.

The same file is read by the PostgreSQL container: changing the password **after** the volume was created has no effect on an existing database (you then need `docker compose down -v`, which deletes the data).

### Health probes

`GET /health` only says the application is running (`200 {"status": "ok"}`), without touching the database: use it as the liveness probe for Docker or a hosting platform, so that a database outage does not make them restart a working application.

`GET /health/db` runs `SELECT 1`: `200 {"status": "ok"}` if the database answers, otherwise `503 {"detail": "Database unavailable", "code": "database_unavailable"}` (the detailed error is in the backend logs).

### Migrations (Alembic)

| Action                              | Command                                                   |
| ----------------------------------- | --------------------------------------------------------- |
| Create a migration from the models  | `uv run alembic revision --autogenerate -m "description"` |
| Apply migrations                    | `uv run alembic upgrade head`                             |
| Revert the last migration           | `uv run alembic downgrade -1`                             |
| Show the database's current version | `uv run alembic current`                                  |

Models must inherit from `app.db.base.Base` and be imported by `migrations/env.py` to be detected by `--autogenerate`. **Always review** a generated migration before applying it.

Constraint and index names follow the naming convention of `app/db/base.py` (`pk_users`, `uq_users_email`, `fk_refresh_tokens_user_id_users`, `ix_refresh_tokens_user_id`…): a migration can refer to them by name without guessing what PostgreSQL chose.

`tests/integration/test_migrations.py` fails when the models and the migrations no longer describe the same schema, or when a migration cannot be rolled back.

---

## 10. Logging

Application logs (loggers under `app`, e.g. `logging.getLogger(__name__)` in `app/...`) are configured by `app/core/logging.py`:

- written to stderr with the **same format as uvicorn**, plus the logger name: `ERROR:    app.main - Échec de la connexion à la base de données`;
- level set by `LOG_LEVEL` (in `.env` or the environment, default `INFO`); an invalid value stops the application at startup with a clear error;
- uvicorn's own logs keep their configuration: use `--log-level` on `fastapi dev` / `fastapi run` to change them.

---

## 11. API contract (OpenAPI)

`openapi.json` is a snapshot of the API contract: the OpenAPI schema FastAPI builds from the routes and Pydantic models (the same one behind `/docs`). It is committed, so every PR shows whether it changes the API, and the frontend **generates its TypeScript types** from it (`pnpm gen:api`) instead of copying them by hand.

When you add or change a route or a Pydantic schema:

1. `uv run python scripts/export_openapi.py` (in `backend/`) updates `openapi.json`;
2. `pnpm gen:api` (in `frontend/`) regenerates the TypeScript types;
3. fix any `pnpm typecheck` error: it shows the frontend code affected by the change;
4. commit `backend/openapi.json` and `frontend/src/api/schema.d.ts` together.

If you forget step 1, the backend test `test_openapi_schema_is_up_to_date` fails; if you forget step 2, the CI step "Check API types are up to date" fails.

---

## 12. Error format

Every error response of the API has the same JSON shape, `ErrorResponse` (`app/core/errors.py`), exposed in the OpenAPI contract:

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

- `code`: stable, machine-readable error code. **The frontend translates the error from `code` and `params`**: it does not display `detail`.
- `params` (optional): values used by the translation (e.g. `min_length`).
- `detail`: English text for developers and logs only.

| Case                                                            | Status        | Body                                                                                                                                                                                                                         |
| --------------------------------------------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AppHTTPException` raised by a route (`app/exceptions/http.py`) | the one given | `detail` + its `code` (an `ErrorCode`) + optional `params`; headers kept (`WWW-Authenticate`, `set-cookie`)                                                                                                                  |
| Other `HTTPException` (e.g. FastAPI's 404/405)                  | the one given | `detail` + `code: "http_error"`                                                                                                                                                                                              |
| Invalid request (path, query, body)                             | `422`         | `code: "validation_error"` + `errors`: one entry per invalid field (`field` = location, `message`, `code` = Pydantic error type such as `missing` or `string_too_short`, `params` = its scalar context such as `min_length`) |
| Unexpected exception                                            | `500`         | `{"detail": "Internal server error", "code": "internal_error"}`: no internal detail is sent to the client; the error is logged with its traceback, method and path                                                           |

Error codes (`ErrorCode`, `app/constants/error_codes.py`):

| Code                        | Status      | Meaning                                                                    |
| --------------------------- | ----------- | -------------------------------------------------------------------------- |
| `internal_error`            | 500         | Unexpected error                                                           |
| `validation_error`          | 422         | Invalid request (see `errors`)                                             |
| `http_error`                | any         | `HTTPException` without a dedicated code                                   |
| `database_unavailable`      | 503         | `GET /health/db`: the database does not answer                             |
| `not_authenticated`         | 401         | Missing or invalid access token                                            |
| `email_already_registered`  | 409         | Registration with an email already used                                    |
| `invalid_credentials`       | 401         | Wrong email or password                                                    |
| `session_expired`           | 401         | Missing, expired or revoked refresh token                                  |
| `incorrect_password`        | 403         | Wrong password when deleting the account                                   |
| `reauthentication_required` | 403         | Google account whose last sign-in is too old to confirm the deletion       |
| `invalid_token`             | 400         | Link received by email invalid, expired, or no longer matching the account |
| `password_too_short`        | 422 (field) | Password shorter than `PASSWORD_MIN_LENGTH`; `params.min_length`           |

For expected errors (not found, conflict…), raise an `AppHTTPException` with an `ErrorCode` and an English `detail` (`app/constants/messages.py`), and let unexpected errors reach the generic handler: never catch `Exception` in a route just to return a 500. **A new error code must be translated in every frontend language.** On the frontend, `ApiError` exposes `status`, `body`, and `detail` as its `message`.
